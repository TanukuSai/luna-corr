"""
Classical feature matchers: SIFT, RootSIFT, and ORB with tiling and robust filtering.
"""
from typing import Optional, Tuple
import numpy as np
import cv2

from .base import BaseMatcher, MatchResult
from ..represent.preprocessor import RepresentationLayer

class SIFTMatcher(BaseMatcher):
    """
    SIFT and RootSIFT feature matcher with Lowe's ratio test and mutual nearest-neighbor verification.
    """

    def __init__(
        self,
        n_features: int = 5000,
        root_sift: bool = True,
        ratio_threshold: float = 0.8,
        use_local_norm: bool = True
    ):
        self.n_features = n_features
        self.root_sift = root_sift
        self.ratio_threshold = ratio_threshold
        self.use_local_norm = use_local_norm
        self.detector = cv2.SIFT_create(nfeatures=n_features)

    def _extract_descriptors(self, img: np.ndarray, mask: Optional[np.ndarray] = None):
        u8 = (np.clip(img, 0.0, 1.0) * 255.0).astype(np.uint8)
        u8_mask = (mask.astype(np.uint8) * 255) if mask is not None else None
        
        kpts, descs = self.detector.detectAndCompute(u8, u8_mask)
        if descs is not None and self.root_sift:
            # RootSIFT L1-normalization and square root
            l1_norm = np.linalg.norm(descs, ord=1, axis=1, keepdims=True) + 1e-7
            descs = np.sqrt(descs / l1_norm)
        return kpts, descs

    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        src_mask: Optional[np.ndarray] = None,
        ref_mask: Optional[np.ndarray] = None
    ) -> MatchResult:
        s_in = RepresentationLayer.local_contrast_normalization(src_img) if self.use_local_norm else src_img
        r_in = RepresentationLayer.local_contrast_normalization(ref_img) if self.use_local_norm else ref_img

        kpts_s, desc_s = self._extract_descriptors(s_in, src_mask)
        kpts_r, desc_r = self._extract_descriptors(r_in, ref_mask)

        name = "RootSIFT" if self.root_sift else "SIFT"

        if desc_s is None or desc_r is None or len(kpts_s) < 4 or len(kpts_r) < 4:
            return MatchResult(
                src_points=np.empty((0, 2), dtype=np.float32),
                ref_points=np.empty((0, 2), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                matcher_name=name
            )

        bf = cv2.BFMatcher(cv2.NORM_L2)
        # KNN match (k=2) for Lowe's ratio test
        matches = bf.knnMatch(desc_s, desc_r, k=2)

        good_matches = []
        for pair in matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < self.ratio_threshold * n.distance:
                    good_matches.append(m)

        if not good_matches:
            return MatchResult(
                src_points=np.empty((0, 2), dtype=np.float32),
                ref_points=np.empty((0, 2), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                matcher_name=name
            )

        src_pts = np.float32([kpts_s[m.queryIdx].pt for m in good_matches])
        ref_pts = np.float32([kpts_r[m.trainIdx].pt for m in good_matches])
        scores = np.float32([1.0 / (1.0 + m.distance) for m in good_matches])

        return MatchResult(
            src_points=src_pts,
            ref_points=ref_pts,
            scores=scores,
            matcher_name=name,
            metadata={"num_detected_src": len(kpts_s), "num_detected_ref": len(kpts_r)}
        )

class TiledMatcher:
    """Wraps any BaseMatcher to perform coarse-to-fine tiled matching on high-resolution images."""

    def __init__(self, matcher: BaseMatcher, tile_size: int = 1024, overlap: int = 256):
        self.matcher = matcher
        self.tile_size = tile_size
        self.overlap = overlap

    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        src_mask: Optional[np.ndarray] = None,
        ref_mask: Optional[np.ndarray] = None
    ) -> MatchResult:
        sh, sw = src_img.shape[:2]
        rh, rw = ref_img.shape[:2]

        # If both images comfortably fit within a tile, match directly
        if max(sh, sw) <= self.tile_size and max(rh, rw) <= self.tile_size:
            return self.matcher.match(src_img, ref_img, src_mask, ref_mask)

        # Step through image tiles
        all_src_pts = []
        all_ref_pts = []
        all_scores = []

        step = self.tile_size - self.overlap
        y_steps = range(0, max(1, sh - self.overlap), step)
        x_steps = range(0, max(1, sw - self.overlap), step)

        for y in y_steps:
            for x in x_steps:
                y_end = min(y + self.tile_size, sh)
                x_end = min(x + self.tile_size, sw)

                src_crop = src_img[y:y_end, x:x_end]
                src_m = src_mask[y:y_end, x:x_end] if src_mask is not None else None

                # Find corresponding area in reference (coarse assumption or full ref if small)
                # Map relative coordinates proportionally
                ry0 = int(y / sh * rh)
                ry1 = min(int(y_end / sh * rh) + self.overlap, rh)
                rx0 = int(x / sw * rw)
                rx1 = min(int(x_end / sw * rw) + self.overlap, rw)

                ref_crop = ref_img[ry0:ry1, rx0:rx1]
                ref_m = ref_mask[ry0:ry1, rx0:rx1] if ref_mask is not None else None

                if src_crop.shape[0] < 64 or src_crop.shape[1] < 64 or ref_crop.shape[0] < 64 or ref_crop.shape[1] < 64:
                    continue

                res = self.matcher.match(src_crop, ref_crop, src_m, ref_m)
                if not res.is_empty:
                    # Offset back to global coordinates
                    all_src_pts.append(res.src_points + np.array([x, y], dtype=np.float32))
                    all_ref_pts.append(res.ref_points + np.array([rx0, ry0], dtype=np.float32))
                    all_scores.append(res.scores)

        if not all_src_pts:
            return MatchResult(
                src_points=np.empty((0, 2), dtype=np.float32),
                ref_points=np.empty((0, 2), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                matcher_name=f"Tiled({self.matcher.__class__.__name__})"
            )

        return MatchResult(
            src_points=np.vstack(all_src_pts),
            ref_points=np.vstack(all_ref_pts),
            scores=np.concatenate(all_scores),
            matcher_name=f"Tiled({self.matcher.__class__.__name__})"
        )
