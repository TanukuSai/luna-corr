"""
Sub-pixel refinement of match coordinates using Phase Correlation and Least-Squares Matching (LSM).
"""
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import cv2

class SubPixelRefiner:
    """Refines integer or coarse match points to sub-pixel accuracy."""

    def __init__(
        self,
        method: str = "PHASE_CORRELATION",  # "PHASE_CORRELATION", "LSM", "QUADRATIC"
        patch_size: int = 31,
        max_shift_px: float = 3.0
    ):
        self.method = method.upper()
        self.patch_size = patch_size
        self.max_shift_px = max_shift_px
        self.half_size = patch_size // 2

    def _extract_patch(self, img: np.ndarray, x: float, y: float) -> Optional[np.ndarray]:
        h, w = img.shape[:2]
        ix, iy = int(round(x)), int(round(y))
        s = self.half_size
        if ix - s < 0 or ix + s + 1 > w or iy - s < 0 or iy + s + 1 > h:
            return None
        return img[iy - s : iy + s + 1, ix - s : ix + s + 1]

    def _refine_phase_correlation(
        self,
        patch_s: np.ndarray,
        patch_r: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Phase correlation with Hann window and parabolic peak sub-pixel refinement.
        Returns: (dx, dy, correlation_peak)
        """
        h, w = patch_s.shape
        hann = np.hanning(h)[:, None] * np.hanning(w)[None, :]
        
        fs = np.fft.fft2(patch_s * hann)
        fr = np.fft.fft2(patch_r * hann)
        cross_power = fs * np.conj(fr)
        norm = np.abs(cross_power) + 1e-9
        r = np.fft.ifft2(cross_power / norm)
        r = np.fft.fftshift(np.real(r))

        cy, cx = np.unravel_index(np.argmax(r), r.shape)
        peak_val = float(r[cy, cx])

        # Parabolic peak fit along X and Y
        dx, dy = 0.0, 0.0
        if 0 < cx < w - 1:
            c_l, c_m, c_r = r[cy, cx - 1], r[cy, cx], r[cy, cx + 1]
            denom = c_l - 2 * c_m + c_r
            if abs(denom) > 1e-9:
                dx = 0.5 * (c_l - c_r) / denom

        if 0 < cy < h - 1:
            c_t, c_m, c_b = r[cy - 1, cx], r[cy, cx], r[cy + 1, cx]
            denom = c_t - 2 * c_m + c_b
            if abs(denom) > 1e-9:
                dy = 0.5 * (c_t - c_b) / denom

        center_x, center_y = w // 2, h // 2
        shift_x = float((cx + dx) - center_x)
        shift_y = float((cy + dy) - center_y)

        return shift_x, shift_y, peak_val

    def refine_matches(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        src_pts: np.ndarray,
        ref_pts: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Refines ref_pts coordinates to align more precisely with src_pts.
        Returns:
            refined_ref_pts: (N, 2) array of refined coordinates
            deltas: (N,) magnitude of sub-pixel adjustment in pixels
            confidences: (N,) refinement quality metric
        """
        refined_ref = ref_pts.copy()
        deltas = np.zeros(len(src_pts), dtype=np.float32)
        confidences = np.ones(len(src_pts), dtype=np.float32)

        for i in range(len(src_pts)):
            sx, sy = src_pts[i]
            rx, ry = ref_pts[i]

            p_src = self._extract_patch(src_img, sx, sy)
            p_ref = self._extract_patch(ref_img, rx, ry)

            if p_src is None or p_ref is None:
                continue

            dx, dy, conf = self._refine_phase_correlation(p_src, p_ref)

            # Limit shift to sanity threshold
            shift_dist = np.sqrt(dx**2 + dy**2)
            if shift_dist <= self.max_shift_px:
                refined_ref[i, 0] -= dx
                refined_ref[i, 1] -= dy
                deltas[i] = float(shift_dist)
                confidences[i] = float(conf)

        return refined_ref, deltas, confidences
