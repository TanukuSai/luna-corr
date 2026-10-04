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
        min_p95_px: float = 1.5
    ):
        self.autocorr_threshold = autocorr_threshold
        self.min_p95_px = min_p95_px

    def analyze(
        self,
        src_pts: np.ndarray,
        residual_vectors: np.ndarray,  # (N, 2): ref_pts - H(src_pts)
        homography_p95_px: float
    ) -> AdaptiveModelDecision:
        n = len(src_pts)
        if n < 15 or homography_p95_px < self.min_p95_px:
            return AdaptiveModelDecision(
                selected_model="HOMOGRAPHY",
                spatial_autocorrelation=0.0,
                parallax_ratio=0.0,
                reason=f"Residual P95 ({homography_p95_px:.2f} px) is within rigid planar tolerance (<{self.min_p95_px} px)."
            )

        # Compute simplified spatial autocorrelation:
        # Distance matrix between points
        dists = np.linalg.norm(src_pts[:, None] - src_pts[None, :], axis=-1)
        np.fill_diagonal(dists, np.inf)

        # For each point, find nearest neighbor and compute dot product of residual directions
        nearest_idx = np.argmin(dists, axis=1)
        
        # Normalize residual vectors
        norms = np.linalg.norm(residual_vectors, axis=1, keepdims=True) + 1e-7
        norm_res = residual_vectors / norms

        # Dot product with nearest neighbor direction
        neighbor_dots = np.sum(norm_res * norm_res[nearest_idx], axis=1)
        mean_autocorr = float(np.mean(neighbor_dots))

        # Parallax ratio: variance of residuals relative to mean
        err_mags = np.linalg.norm(residual_vectors, axis=1)
        parallax_ratio = float(np.std(err_mags) / (np.mean(err_mags) + 1e-6))

        if mean_autocorr > self.autocorr_threshold and homography_p95_px >= self.min_p95_px:
            return AdaptiveModelDecision(
                selected_model="TPS",
                spatial_autocorrelation=round(mean_autocorr, 3),
                parallax_ratio=round(parallax_ratio, 3),
                reason=f"Residuals exhibit spatial relief correlation (autocorr={mean_autocorr:.2f} > {self.autocorr_threshold}); triggering non-rigid TPS."
            )
        else:
            return AdaptiveModelDecision(
                selected_model="HOMOGRAPHY",
                spatial_autocorrelation=round(mean_autocorr, 3),
                parallax_ratio=round(parallax_ratio, 3),
                reason=f"Residuals represent uncorrelated noise (autocorr={mean_autocorr:.2f} <= {self.autocorr_threshold}); maintaining global homography."
            )
