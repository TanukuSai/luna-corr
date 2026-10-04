"""
Local non-rigid and elastic transformation models (Thin-Plate Spline & Displacement Fields).
Absorbs 3D relief parallax and push-broom trajectory jitter beyond flat-world homographies.
"""
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import numpy as np
import cv2
from scipy.interpolate import RBFInterpolator

@dataclass
class NonRigidResult:
    warp_type: str  # "TPS" (Thin-Plate Spline) or "HOMOGRAPHY_PLUS_DISPLACEMENT"
    control_points_src: np.ndarray  # (K, 2)
    control_points_ref: np.ndarray  # (K, 2)
    residuals: np.ndarray  # (K,) residual errors after elastic fitting
    rmse: float
    median_error: float
    p95_error: float
    rbf_model: Optional[Any] = None

class ElasticTransformer:
    """
    Fits a smooth Thin-Plate Spline (TPS) transformation over spatially uniform tie points.
    Provides sub-pixel deformation to compensate for lunar topography relief parallax.
    """

    def __init__(self, smoothing: float = 0.5, kernel: str = "thin_plate_spline"):
        self.smoothing = smoothing
        self.kernel = kernel

    def fit(
        self,
        src_pts: np.ndarray,
        ref_pts: np.ndarray,
        sample_limit: int = 250
    ) -> Optional[NonRigidResult]:
        """
        Fits a 2D Thin-Plate Spline mapping src_pts -> ref_pts.
        """
        n = len(src_pts)
        if n < 6:
            return None

        # If too many points, subsample uniformly to keep RBF solve fast and smooth
        if n > sample_limit:
            step = n // sample_limit
            idx = np.arange(0, n, step)[:sample_limit]
            fit_src = src_pts[idx]
            fit_ref = ref_pts[idx]
        else:
            fit_src = src_pts
            fit_ref = ref_pts

        # RBF interpolator mapping (x, y) -> (dx, dy) = ref - src
        diff = fit_ref - fit_src
        try:
            rbf = RBFInterpolator(
                fit_src, diff,
                kernel=self.kernel,
                smoothing=self.smoothing
            )
        except Exception:
            return None

        # Predict displacements on all points
        predicted_diff = rbf(src_pts)
        predicted_ref = src_pts + predicted_diff

        errors = np.linalg.norm(predicted_ref - ref_pts, axis=1)

        return NonRigidResult(
            warp_type="TPS",
            control_points_src=fit_src,
            control_points_ref=fit_ref,
            residuals=errors,
            rmse=float(np.sqrt(np.mean(errors ** 2))),
            median_error=float(np.median(errors)),
            p95_error=float(np.percentile(errors, 95)),
            rbf_model=rbf
        )

    def warp_image(
        self,
        img: np.ndarray,
        target_shape: Tuple[int, int],
        rbf_model: Any,
        grid_step: int = 16
    ) -> np.ndarray:
        """
        Warps source image into reference frame using dense displacement meshgrid.
        Computes forward-backward mapping via dense grid interpolation for high performance.
        """
        th, tw = target_shape[:2]
        
        # Build coarse grid in reference space to invert mapping
        gy, gx = np.mgrid[0:th:grid_step, 0:tw:grid_step]
        grid_ref = np.vstack([gx.ravel(), gy.ravel()]).T

        # Inverse shift: where did this ref pixel come from in src?
        # Initial approximation: src approx ref - delta
        shifts = rbf_model(grid_ref)
        grid_src = grid_ref - shifts

        # Interpolate dense pixel map using cv2.remap
        map_x = cv2.resize(grid_src[:, 0].reshape(gy.shape).astype(np.float32), (tw, th), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(grid_src[:, 1].reshape(gy.shape).astype(np.float32), (tw, th), interpolation=cv2.INTER_CUBIC)

        warped = cv2.remap(
            img, map_x, map_y,
            interpolation=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0
        )
        return warped
