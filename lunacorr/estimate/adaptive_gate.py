"""
Adaptive model selection gate.
Decides whether to keep a global homography or trigger elastic Thin-Plate Spline (TPS)
based on residual spatial autocorrelation and parallax variance.
"""
from dataclasses import dataclass
from typing import Tuple, Dict, Any
import numpy as np

@dataclass
class AdaptiveModelDecision:
    selected_model: str  # "HOMOGRAPHY" or "TPS"
    spatial_autocorrelation: float
    parallax_ratio: float
    reason: str

class AdaptiveDeformationGate:
    """
    Prevents unconditional non-rigid overfitting.
    Only triggers TPS if residual vectors display spatial curvature/relief parallax.
    """

    def __init__(
        self,
        autocorr_threshold: float = 0.20,
        min_p95_px: float = 1.5,
        eps_zero: float = 0.05,
        min_points: int = 15
    ):
        self.autocorr_threshold = autocorr_threshold
        self.min_p95_px = min_p95_px
        self.eps_zero = eps_zero
        self.min_points = min_points

    def analyze(
        self,
        src_pts: np.ndarray,
        residual_vectors: np.ndarray,  # (N, 2): ref_pts - H(src_pts)
        homography_p95_px: float
    ) -> AdaptiveModelDecision:
        n = len(src_pts)
        if n < self.min_points or homography_p95_px < self.min_p95_px:
            return AdaptiveModelDecision(
                selected_model="HOMOGRAPHY",
                spatial_autocorrelation=0.0,
                parallax_ratio=0.0,
                reason=f"Residual P95 ({homography_p95_px:.2f} px) is within rigid planar tolerance (<{self.min_p95_px} px) or points ({n}) < {self.min_points}."
            )

        err_mags = np.linalg.norm(residual_vectors, axis=1)
        valid_mask = err_mags >= self.eps_zero

        if np.sum(valid_mask) < self.min_points:
            return AdaptiveModelDecision(
                selected_model="HOMOGRAPHY",
                spatial_autocorrelation=0.0,
                parallax_ratio=0.0,
                reason=f"Insufficient non-zero residual vectors (>={self.eps_zero} px) to evaluate spatial correlation."
            )

        valid_src = src_pts[valid_mask]
        valid_res = residual_vectors[valid_mask]
        valid_mags = err_mags[valid_mask]

        # Compute deterministic nearest-neighbor directional residual correlation (NN-DRC)
        dists = np.linalg.norm(valid_src[:, None] - valid_src[None, :], axis=-1)
        np.fill_diagonal(dists, np.inf)

        nearest_idx = np.argmin(dists, axis=1)
        norm_res = valid_res / valid_mags[:, None]

        # Dot product of normalized residual directions between spatial nearest neighbors
        neighbor_dots = np.sum(norm_res * norm_res[nearest_idx], axis=1)
        mean_autocorr = float(np.mean(neighbor_dots))

        # Parallax ratio: variance of residuals relative to mean
        parallax_ratio = float(np.std(valid_mags) / (np.mean(valid_mags) + 1e-6))

        # Scientific dual-condition trigger: S_relief > autocorr_threshold AND P95 >= min_p95_px
        if mean_autocorr > self.autocorr_threshold and homography_p95_px >= self.min_p95_px:
            return AdaptiveModelDecision(
                selected_model="TPS",
                spatial_autocorrelation=round(mean_autocorr, 3),
                parallax_ratio=round(parallax_ratio, 3),
                reason=f"Residuals exhibit spatial relief correlation (autocorr={mean_autocorr:.2f} > {self.autocorr_threshold}) and P95 ({homography_p95_px:.2f} px >= {self.min_p95_px} px); triggering non-rigid TPS."
            )
        else:
            return AdaptiveModelDecision(
                selected_model="HOMOGRAPHY",
                spatial_autocorrelation=round(mean_autocorr, 3),
                parallax_ratio=round(parallax_ratio, 3),
                reason=f"Residuals represent uncorrelated noise (autocorr={mean_autocorr:.2f} <= {self.autocorr_threshold}); maintaining global homography."
            )
