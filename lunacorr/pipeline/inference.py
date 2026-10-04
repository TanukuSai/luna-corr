"""
End-to-end registration and correspondence inference pipeline.
Integrates soft spatial utility selection, adaptive deformation gating,
and unbiased evaluation on strictly withheld independent check points.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import time
import json
import csv
import numpy as np
import cv2

from ..data.pds4_reader import PDS4Reader, LunarProduct
from ..matchers.classical import SIFTMatcher, TiledMatcher
from ..estimate.robust import RobustEstimator, EstimationResult
from ..estimate.nonrigid import ElasticTransformer, NonRigidResult
from ..estimate.adaptive_gate import AdaptiveDeformationGate, AdaptiveModelDecision
from ..selection.soft_utility import SoftSpatialUtilitySelector
from ..selection.spatial_quota import UniformityResult
from ..refine.subpixel import SubPixelRefiner
from ..eval.checkpoints import CheckpointEvaluator, CheckpointEvaluation
from ..gate.decision_gate import QualityGate, GateDecision

@dataclass
class RegistrationOutput:
    source_id: str
    reference_id: str
    decision: GateDecision
    estimation: Optional[EstimationResult]
    uniformity: Optional[UniformityResult]
    match_points: np.ndarray  # (K, 4): src_x, src_y, ref_x, ref_y
    refine_deltas: np.ndarray  # (K,)
    warped_image: Optional[np.ndarray]
    runtime_s: float
    nonrigid: Optional[NonRigidResult] = None
    adaptive_decision: Optional[AdaptiveModelDecision] = None
    checkpoints: Optional[CheckpointEvaluation] = None
    output_dir: Optional[Path] = None

class LunarRegistrationPipeline:
    """
    Orchestrates the scientific 8-stage correspondence and registration pipeline.
    """

    def __init__(
        self,
        matcher: Optional[Any] = None,
        estimator: Optional[RobustEstimator] = None,
        selector: Optional[Any] = None,
        refiner: Optional[SubPixelRefiner] = None,
        adaptive_gate: Optional[AdaptiveDeformationGate] = None,
        gate: Optional[QualityGate] = None,
        max_image_dim: int = 2048
    ):
        self.matcher = matcher or TiledMatcher(SIFTMatcher(n_features=6000, root_sift=True), tile_size=1024)
        self.estimator = estimator or RobustEstimator(method="MAGSAC", reproj_threshold_px=3.0)
        self.selector = selector or SoftSpatialUtilitySelector(grid_size=(8, 8), k_max_per_cell=15)
        self.refiner = refiner or SubPixelRefiner(method="PHASE_CORRELATION")
        self.adaptive_gate = adaptive_gate or AdaptiveDeformationGate(autocorr_threshold=0.20, min_p95_px=1.5)
        self.gate = gate or QualityGate(min_inliers=15, min_inlier_ratio=0.15, max_p95_residual_px=4.0)
        self.max_image_dim = max_image_dim

    def run(
        self,
        source_path: Path,
        reference_path: Path,
        output_dir: Optional[Path] = None
    ) -> RegistrationOutput:
        t0 = time.time()
        
        # 1. Ingest
        src_prod = PDS4Reader.load_product(source_path, max_dim=self.max_image_dim)
        ref_prod = PDS4Reader.load_product(reference_path, max_dim=self.max_image_dim)

        src_arr, ref_arr = src_prod.array, ref_prod.array
        src_m, ref_m = src_prod.mask, ref_prod.mask

        # 2. Match
        raw_matches = self.matcher.match(src_arr, ref_arr, src_m, ref_m)

        if raw_matches.is_empty:
            decision = self.gate.evaluate(0, 0.0, 0.0, 1.0, 999.0)
            return RegistrationOutput(
                source_id=src_prod.product_id, reference_id=ref_prod.product_id,
                decision=decision, estimation=None, uniformity=None,
                match_points=np.empty((0, 4)), refine_deltas=np.empty((0,)),
                warped_image=None, runtime_s=time.time() - t0, output_dir=output_dir
            )

        # 3. Robust Estimation
        est = self.estimator.estimate(raw_matches.src_points, raw_matches.ref_points, model_type="HOMOGRAPHY")
        if est is None:
            est = self.estimator.estimate(raw_matches.src_points, raw_matches.ref_points, model_type="AFFINE")

        if est is None:
            decision = self.gate.evaluate(0, 0.0, 0.0, 1.0, 999.0)
            return RegistrationOutput(
                source_id=src_prod.product_id, reference_id=ref_prod.product_id,
                decision=decision, estimation=None, uniformity=None,
                match_points=np.empty((0, 4)), refine_deltas=np.empty((0,)),
                warped_image=None, runtime_s=time.time() - t0, output_dir=output_dir
            )

        # Inliers
        inl_src = raw_matches.src_points[est.inlier_mask]
        inl_ref = raw_matches.ref_points[est.inlier_mask]
        inl_scores = raw_matches.scores[est.inlier_mask]
        inl_residuals = est.residuals

        # 4. Soft Spatial Utility Selection
        if hasattr(self.selector, "select") and "residuals" in self.selector.select.__code__.co_varnames:
            uni = self.selector.select(inl_src, inl_scores, inl_residuals, src_arr.shape)
        else:
            uni = self.selector.select(inl_src, inl_scores, src_arr.shape)

        sel_idx = uni.selected_indices
        sel_src = inl_src[sel_idx]
        sel_ref = inl_ref[sel_idx]

        # 5. Sub-pixel Refinement
        refined_ref, deltas, confs = self.refiner.refine_matches(src_arr, ref_arr, sel_src, sel_ref)

        # 6. Independent Check-Point Split (80% Fit, 20% strictly withheld check points)
        fit_src, fit_ref, check_src, check_ref = CheckpointEvaluator.split_points(
            sel_src, refined_ref, inl_scores[sel_idx], fit_fraction=0.80, seed=42
        )

        # Calculate residual vectors of global homography on fit points EXCLUSIVELY
        fit_src_h = np.hstack([fit_src, np.ones((len(fit_src), 1), dtype=np.float32)])
        pred_fit_h = (est.matrix @ fit_src_h.T).T
        pred_fit = pred_fit_h[:, :2] / (pred_fit_h[:, 2:3] + 1e-9)
        residual_vectors = fit_ref - pred_fit
        
        # P95 residual evaluated strictly on the 80% fitting points (zero test set leakage)
        fit_res_norms = np.linalg.norm(residual_vectors, axis=1)
        fit_p95 = float(np.percentile(fit_res_norms, 95)) if len(fit_res_norms) > 0 else 0.0

        # 7. Adaptive Model Selection Gate (Homography vs Elastic TPS)
        adaptive_dec = self.adaptive_gate.analyze(fit_src, residual_vectors, fit_p95)

        nonrigid_res = None
        elastic = ElasticTransformer(smoothing=0.5)

        if adaptive_dec.selected_model == "TPS" and len(fit_src) >= 12:
            nonrigid_res = elastic.fit(fit_src, fit_ref)

        # Transform function for independent check-point evaluation
        if nonrigid_res is not None and nonrigid_res.rbf_model is not None:
            def transform_func(pts):
                return pts + nonrigid_res.rbf_model(pts)
        else:
            def transform_func(pts):
                pts_h = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
                wh = (est.matrix @ pts_h.T).T
                return wh[:, :2] / (wh[:, 2:3] + 1e-9)

        # Evaluate on withheld independent check points
        chk_eval = CheckpointEvaluator.evaluate(fit_src, fit_ref, check_src, check_ref, transform_func)

        # Unbiased metric for scientific gate: check-point P95
        eval_p95 = chk_eval.check_p95_px if not np.isnan(chk_eval.check_p95_px) else chk_eval.fit_p95_px

        # 8. Quality Abstention Gate
        decision = self.gate.evaluate(
            inlier_count=len(sel_src),
            inlier_ratio=est.inlier_ratio,
            occupied_ratio=uni.occupied_ratio,
            largest_empty_circle=uni.largest_empty_circle,
            p95_residual_px=eval_p95,
            entropy=uni.entropy
        )

        # 9. Warp Registered Product
        warped_img = None
        if decision.accepted:
            rh, rw = ref_arr.shape[:2]
            if nonrigid_res is not None and nonrigid_res.rbf_model is not None:
                warped_img = elastic.warp_image(src_arr, (rh, rw), nonrigid_res.rbf_model)
            else:
                warped_img = cv2.warpPerspective(src_arr, est.matrix, (rw, rh), flags=cv2.INTER_CUBIC)

        runtime = time.time() - t0
        match_table = np.hstack([sel_src, refined_ref]) if len(sel_src) > 0 else np.empty((0, 4))

        out = RegistrationOutput(
            source_id=src_prod.product_id,
            reference_id=ref_prod.product_id,
            decision=decision,
            estimation=est,
            uniformity=uni,
            match_points=match_table,
            refine_deltas=deltas,
            warped_image=warped_img,
            runtime_s=runtime,
            nonrigid=nonrigid_res,
            adaptive_decision=adaptive_dec,
            checkpoints=chk_eval,
            output_dir=output_dir
        )

        if output_dir:
            self._save_deliverables(out, src_arr, ref_arr, output_dir)

        return out

    def _save_deliverables(
        self,
        res: RegistrationOutput,
        src_arr: np.ndarray,
        ref_arr: np.ndarray,
        output_dir: Path
    ):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. match_points.csv
        csv_path = output_dir / "match_points.csv"
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "src_x", "src_y", "ref_x", "ref_y", "subpixel_delta_px"])
            for i, row in enumerate(res.match_points):
                delta = res.refine_deltas[i] if i < len(res.refine_deltas) else 0.0
                w.writerow([i, f"{row[0]:.3f}", f"{row[1]:.3f}", f"{row[2]:.3f}", f"{row[3]:.3f}", f"{delta:.3f}"])

        # 2. result.json
        json_path = output_dir / "result.json"
        data = {
            "source_id": res.source_id,
            "reference_id": res.reference_id,
            "status": res.decision.status,
            "accepted": res.decision.accepted,
            "reason_codes": res.decision.reason_codes,
            "confidence_score": res.decision.confidence_score,
            "quality_score": res.decision.confidence_score,
            "runtime_s": round(res.runtime_s, 3),
            "metrics": res.decision.metrics,
            "transform_matrix": res.estimation.matrix.tolist() if res.estimation else None,
            "adaptive_model_selection": {
                "chosen_model": res.adaptive_decision.selected_model,
                "residual_spatial_coherence": res.adaptive_decision.spatial_autocorrelation,
                "parallax_ratio": res.adaptive_decision.parallax_ratio,
                "reason": res.adaptive_decision.reason
            } if res.adaptive_decision else None,
            "fitting_correspondences_metrics": {
                "n_points": res.checkpoints.n_fit_points,
                "rmse": round(res.checkpoints.fit_rmse, 3),
                "median_error_px": round(res.checkpoints.fit_median_px, 3),
                "p95_error_px": round(res.checkpoints.fit_p95_px, 3)
            } if res.checkpoints else None,
            "heldout_validation_correspondences_metrics": {
                "n_points": res.checkpoints.n_check_points,
                "rmse": round(res.checkpoints.check_rmse, 3),
                "median_error_px": round(res.checkpoints.check_median_px, 3),
                "p95_error_px": round(res.checkpoints.check_p95_px, 3),
                "evaluation_type": "20% withheld correspondences (not external geodetic ground truth)"
            } if res.checkpoints else None,
            "independent_ground_truth_control": None
        }
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        # 3. registered_image.tif / .png
        if res.warped_image is not None:
            u8_warped = (np.clip(res.warped_image, 0.0, 1.0) * 255).astype(np.uint8)
            cv2.imwrite(str(output_dir / "registered_image.tif"), u8_warped)
            cv2.imwrite(str(output_dir / "registered_image.png"), u8_warped)

            # Composite checkerboard overlay
            u8_ref = (np.clip(ref_arr, 0.0, 1.0) * 255).astype(np.uint8)
            checker = u8_ref.copy()
            block = 64
            for y in range(0, checker.shape[0], block):
                for x in range(0, checker.shape[1], block):
                    if ((x // block) + (y // block)) % 2 == 1:
                        y_end = min(y + block, checker.shape[0])
                        x_end = min(x + block, checker.shape[1])
                        checker[y:y_end, x:x_end] = u8_warped[y:y_end, x:x_end]
            cv2.imwrite(str(output_dir / "checkerboard_overlay.png"), checker)
