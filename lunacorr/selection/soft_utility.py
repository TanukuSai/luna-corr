"""
Soft spatial utility selector.
Balances correspondence confidence, spatial coverage, and reprojection residual:
Score = alpha * Confidence + beta * Spatial_Coverage + gamma * Diversity - lambda * Residual
Never forces low-confidence matches into featureless mare terrain.
"""
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional
import numpy as np

from .spatial_quota import UniformityResult, SpatialUniformitySelector

class SoftSpatialUtilitySelector:
    """
    Selects tie points maximizing global utility while protecting against forced false matches.
    """

    def __init__(
        self,
        grid_size: Tuple[int, int] = (8, 8),
        alpha: float = 0.40,   # Confidence weight
        beta: float = 0.30,    # Cell representation bonus
        gamma: float = 0.15,   # Spatial diversity weight
        lam: float = 0.15,     # Residual penalty weight
        min_confidence: float = 0.25,
        k_max_per_cell: int = 15
    ):
        self.grid_size = grid_size
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.lam = lam
        self.min_confidence = min_confidence
        self.k_max = k_max_per_cell
        self._quota_calc = SpatialUniformitySelector(grid_size=grid_size)

    def select(
        self,
        src_pts: np.ndarray,
        scores: np.ndarray,
        residuals: np.ndarray,
        image_shape: Tuple[int, int]
    ) -> UniformityResult:
        n = len(src_pts)
        if n == 0:
            return self._quota_calc.select(src_pts, scores, image_shape)

        h, w = image_shape[:2]
        gy, gx = self.grid_size
        diag = np.sqrt(h**2 + w**2)

        # 1. Filter out absolute low-confidence points
        valid_conf_mask = scores >= self.min_confidence
        if not np.any(valid_conf_mask):
            return self._quota_calc.select(np.empty((0, 2)), np.empty((0,)), image_shape)

        ix = np.clip((src_pts[:, 0] / w * gx).astype(int), 0, gx - 1)
        iy = np.clip((src_pts[:, 1] / h * gy).astype(int), 0, gy - 1)
        cell_ids = iy * gx + ix

        # Normalized residuals in [0, 1]
        max_res = np.percentile(residuals, 95) + 1e-6
        norm_res = np.clip(residuals / max_res, 0.0, 1.0)

        selected_indices = []

        for cell in np.unique(cell_ids):
            c_idx = np.where((cell_ids == cell) & valid_conf_mask)[0]
            if len(c_idx) == 0:
                continue

            # Greedy selection within this cell
            cell_selected = []
            c_pts = src_pts[c_idx]
            c_scores = scores[c_idx]
            c_errs = norm_res[c_idx]

            # Sort candidate by raw confidence
            cand_order = list(np.argsort(-c_scores))

            while cand_order and len(cell_selected) < self.k_max:
                best_i = None
                best_val = -float("inf")

                for cand in cand_order:
                    conf = c_scores[cand]
                    err_pen = c_errs[cand]
                    # Diversity: min distance to already selected points in this cell
                    if cell_selected:
                        curr_pt = c_pts[cand]
                        sel_pts_arr = c_pts[cell_selected]
                        div = np.min(np.linalg.norm(sel_pts_arr - curr_pt, axis=1)) / (diag / gx)
                        div = min(1.0, div)
                    else:
                        div = 1.0

                    utility = (
                        self.alpha * conf +
                        self.beta * 1.0 +
                        self.gamma * div -
                        self.lam * err_pen
                    )

                    if utility > best_val:
                        best_val = utility
                        best_i = cand

                if best_i is not None and best_val > 0.1:
                    cell_selected.append(best_i)
                    cand_order.remove(best_i)
                else:
                    break

            selected_indices.extend(c_idx[cell_selected])

        selected = np.array(sorted(selected_indices), dtype=int)
        sel_pts = src_pts[selected] if len(selected) > 0 else np.empty((0, 2))

        occ, ent, empty_circ, counts = self._quota_calc.compute_coverage_metrics(sel_pts, image_shape)

        return UniformityResult(
            selected_indices=selected,
            occupied_ratio=occ,
            entropy=ent,
            largest_empty_circle=empty_circ,
            cell_counts=counts
        )
