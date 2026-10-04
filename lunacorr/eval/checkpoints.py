"""
Independent check-point protocol for unbiased evaluation of registration accuracy.
Splits inlier correspondences into fitting points (80%) and strictly withheld check points (20%).
"""
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
import numpy as np

@dataclass
class CheckpointEvaluation:
    n_fit_points: int
    n_check_points: int
    fit_rmse: float
    fit_median_px: float
    fit_p95_px: float
    check_rmse: float
    check_median_px: float
    check_p95_px: float
    check_errors: np.ndarray

class CheckpointEvaluator:
    """
    Separates estimation from evaluation.
    Measures generalization error on withheld check points that did not participate in fitting.
    """

    @staticmethod
    def split_points(
        src_pts: np.ndarray,
        ref_pts: np.ndarray,
        scores: np.ndarray,
        fit_fraction: float = 0.8,
        seed: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Splits correspondences into (fit_src, fit_ref, check_src, check_ref).
        Stratified or random split with fixed seed.
        """
        n = len(src_pts)
        if n < 8:
            return src_pts, ref_pts, np.empty((0, 2)), np.empty((0, 2))

        rng = np.random.default_rng(seed)
        perm = rng.permutation(n)
        split_idx = int(n * fit_fraction)

        fit_idx = perm[:split_idx]
        check_idx = perm[split_idx:]

        return (
            src_pts[fit_idx],
            ref_pts[fit_idx],
            src_pts[check_idx],
            ref_pts[check_idx]
        )

    @staticmethod
    def evaluate(
        fit_src: np.ndarray,
        fit_ref: np.ndarray,
        check_src: np.ndarray,
        check_ref: np.ndarray,
        transform_func  # Callable: pts -> warped_pts
    ) -> CheckpointEvaluation:
        # 1. Fit residuals (optimistic)
        pred_fit = transform_func(fit_src)
        fit_errs = np.linalg.norm(pred_fit - fit_ref, axis=1)

        # 2. Check points (unbiased independent accuracy)
        if len(check_src) > 0:
            pred_check = transform_func(check_src)
            check_errs = np.linalg.norm(pred_check - check_ref, axis=1)
        else:
            check_errs = np.array([float("nan")])

        return CheckpointEvaluation(
            n_fit_points=len(fit_src),
            n_check_points=len(check_src),
            fit_rmse=float(np.sqrt(np.mean(fit_errs ** 2))),
            fit_median_px=float(np.median(fit_errs)),
            fit_p95_px=float(np.percentile(fit_errs, 95)),
            check_rmse=float(np.sqrt(np.mean(check_errs ** 2))) if len(check_src) > 0 else float("nan"),
            check_median_px=float(np.median(check_errs)) if len(check_src) > 0 else float("nan"),
            check_p95_px=float(np.percentile(check_errs, 95)) if len(check_src) > 0 else float("nan"),
            check_errors=check_errs
        )
