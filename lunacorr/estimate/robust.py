"""
Robust geometric model estimation using MAGSAC++ and RANSAC with model selection.
"""
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import numpy as np
import cv2

@dataclass
class EstimationResult:
    model_type: str  # "HOMOGRAPHY", "AFFINE", "SIMILARITY"
    matrix: np.ndarray  # 3x3 transformation matrix
    inlier_mask: np.ndarray  # (N,) boolean mask
    inlier_count: int
    inlier_ratio: float
    residuals: np.ndarray  # Reprojection errors for inliers
    rmse: float
    median_error: float
    p95_error: float

class RobustEstimator:
    """Estimates geometric transformation between source and reference points."""

    def __init__(
        self,
        method: str = "MAGSAC",  # "MAGSAC" or "RANSAC"
        reproj_threshold_px: float = 3.0,
        confidence: float = 0.999,
        max_iters: int = 5000
    ):
        self.method = method
        self.reproj_threshold_px = reproj_threshold_px
        self.confidence = confidence
        self.max_iters = max_iters

    def estimate(
        self,
        src_pts: np.ndarray,
        ref_pts: np.ndarray,
        model_type: str = "HOMOGRAPHY"
    ) -> Optional[EstimationResult]:
        """
        Fits transformation mapping src_pts -> ref_pts.
        """
        if len(src_pts) < 4 or len(ref_pts) < 4:
            return None

        src_pts = np.ascontiguousarray(src_pts, dtype=np.float32)
        ref_pts = np.ascontiguousarray(ref_pts, dtype=np.float32)

        flag = cv2.USAC_MAGSAC if self.method.upper() == "MAGSAC" else cv2.RANSAC

        if model_type.upper() == "HOMOGRAPHY":
            H, inliers = cv2.findHomography(
                src_pts, ref_pts,
                method=flag,
                ransacReprojThreshold=self.reproj_threshold_px,
                maxIters=self.max_iters,
                confidence=self.confidence
            )
            if H is None:
                return None
            M = H
        elif model_type.upper() in ["AFFINE", "SIMILARITY"]:
            full_affine = (model_type.upper() == "AFFINE")
            aff, inliers = cv2.estimateAffine2D(
                src_pts, ref_pts,
                method=flag,
                ransacReprojThreshold=self.reproj_threshold_px,
                maxIters=self.max_iters,
                confidence=self.confidence
            )
            if aff is None:
                return None
            M = np.eye(3, dtype=np.float32)
            M[:2, :] = aff
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        inliers = inliers.ravel().astype(bool)
        n_inl = int(np.sum(inliers))
        if n_inl < 4:
            return None

        # Calculate reprojection residuals for inliers
        src_inl = src_pts[inliers]
        ref_inl = ref_pts[inliers]
        
        # Warp src points
        src_h = np.hstack([src_inl, np.ones((len(src_inl), 1), dtype=np.float32)])
        warped_h = (M @ src_h.T).T
        warped = warped_h[:, :2] / (warped_h[:, 2:3] + 1e-9)

        errors = np.linalg.norm(warped - ref_inl, axis=1)

        return EstimationResult(
            model_type=model_type.upper(),
            matrix=M,
            inlier_mask=inliers,
            inlier_count=n_inl,
            inlier_ratio=float(n_inl / len(src_pts)),
            residuals=errors,
            rmse=float(np.sqrt(np.mean(errors ** 2))),
            median_error=float(np.median(errors)),
            p95_error=float(np.percentile(errors, 95))
        )
