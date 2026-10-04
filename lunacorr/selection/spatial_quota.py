"""
Spatial uniformity selector and coverage metrics as mandated by PS 26166.
Enforces uniform spatial distribution of match points across the entire image field.
"""
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
from scipy.spatial import KDTree

@dataclass
class UniformityResult:
    selected_indices: np.ndarray  # Indices into the original inlier set
    occupied_ratio: float         # Fraction of grid cells with >= 1 match
    entropy: float                # Normalized entropy of point distribution [0, 1]
    largest_empty_circle: float   # Max radius of empty circle relative to image diagonal
    cell_counts: np.ndarray       # Grid cell count histogram

class SpatialUniformitySelector:
    """
    Partitions the image into an M x N grid and enforces quotas per cell
    to guarantee uniform coverage and prevent localized clustering.
    """

    def __init__(
        self,
        grid_size: Tuple[int, int] = (8, 8),
        k_min: int = 1,
        k_max: int = 15
    ):
        self.grid_size = grid_size
        self.k_min = k_min
        self.k_max = k_max

    def compute_coverage_metrics(
        self,
        points: np.ndarray,
        image_shape: Tuple[int, int]
    ) -> Tuple[float, float, float, np.ndarray]:
        """
        Computes occupied ratio, normalized entropy, and largest empty circle.
        """
        if len(points) == 0:
            return 0.0, 0.0, 1.0, np.zeros(self.grid_size[0] * self.grid_size[1], dtype=int)

        h, w = image_shape[:2]
        gy, gx = self.grid_size

        ix = np.clip((points[:, 0] / w * gx).astype(int), 0, gx - 1)
        iy = np.clip((points[:, 1] / h * gy).astype(int), 0, gy - 1)
        cell_ids = iy * gx + ix

        total_cells = gx * gy
        counts = np.bincount(cell_ids, minlength=total_cells)
        
        # 1. Occupied ratio
        occupied = float(np.mean(counts > 0))

        # 2. Normalized spatial entropy
        valid_counts = counts[counts > 0]
        if len(valid_counts) > 0 and counts.sum() > 0:
            probs = valid_counts / counts.sum()
            ent = -np.sum(probs * np.log(probs)) / np.log(total_cells)
        else:
            ent = 0.0

        # 3. Largest empty circle
        # Sample regular test points across image and measure distance to nearest match
        diag = np.sqrt(w**2 + h**2)
        grid_y, grid_x = np.mgrid[h*0.05:h*0.95:20j, w*0.05:w*0.95:20j]
        test_pts = np.vstack([grid_x.ravel(), grid_y.ravel()]).T

        tree = KDTree(points)
        dists, _ = tree.query(test_pts)
        max_empty_radius = float(np.max(dists) / diag)

        return occupied, float(ent), max_empty_radius, counts

    def select(
        self,
        points: np.ndarray,
        scores: np.ndarray,
        image_shape: Tuple[int, int]
    ) -> UniformityResult:
        """
        Selects up to k_max matches per cell ranked by score to ensure uniform spatial distribution.
        """
        if len(points) == 0:
            return UniformityResult(
                selected_indices=np.empty((0,), dtype=int),
                occupied_ratio=0.0,
                entropy=0.0,
                largest_empty_circle=1.0,
                cell_counts=np.zeros(self.grid_size[0] * self.grid_size[1], dtype=int)
            )

        h, w = image_shape[:2]
        gy, gx = self.grid_size

        ix = np.clip((points[:, 0] / w * gx).astype(int), 0, gx - 1)
        iy = np.clip((points[:, 1] / h * gy).astype(int), 0, gy - 1)
        cell_ids = iy * gx + ix

        selected = []
        unique_cells = np.unique(cell_ids)

        for cell in unique_cells:
            cell_idx = np.where(cell_ids == cell)[0]
            # Rank inliers within this cell by score (descending)
            ranked = cell_idx[np.argsort(-scores[cell_idx])]
            selected.extend(ranked[:self.k_max])

        selected = np.array(sorted(selected), dtype=int)
        sel_pts = points[selected]

        occ, ent, empty_circ, counts = self.compute_coverage_metrics(sel_pts, image_shape)

        return UniformityResult(
            selected_indices=selected,
            occupied_ratio=occ,
            entropy=ent,
            largest_empty_circle=empty_circ,
            cell_counts=counts
        )
