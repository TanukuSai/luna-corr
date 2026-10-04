"""
Windowed block reader for massive Chandrayaan-2 push-broom arrays (e.g. OHRC 93,686 x 12,000).
Uses buffered file-seek windowing to read high-resolution sub-swaths and decimation overviews
with zero memory-mapping overhead and minimal RAM usage (<10 MB).
"""
from pathlib import Path
from typing import Tuple, Optional
import numpy as np

class WindowedPyramidReader:
    """
    Reads large raw/calibrated binary products (.img) using direct line-seek I/O.
    Immune to OS memory commit limits on multi-gigabyte rasters.
    """

    def __init__(self, img_path: Path, lines: int, samples: int, itemsize: int = 2, dtype=np.uint16):
        self.img_path = Path(img_path)
        self.lines = lines
        self.samples = samples
        self.itemsize = itemsize
        self.dtype = dtype
        self.row_stride = samples * itemsize

        if not self.img_path.exists():
            raise FileNotFoundError(f"Binary file not found: {self.img_path}")

    def read_window(
        self,
        y0: int,
        y1: int,
        x0: int,
        x1: int
    ) -> np.ndarray:
        """
        Extracts a high-resolution sub-pixel patch on-demand directly into memory.
        Reads only the requested row segments.
        """
        y0 = max(0, min(self.lines - 1, y0))
        y1 = max(1, min(self.lines, y1))
        x0 = max(0, min(self.samples - 1, x0))
        x1 = max(1, min(self.samples, x1))

        width = x1 - x0
        height = y1 - y0
        patch = np.empty((height, width), dtype=self.dtype)

        bytes_per_row = width * self.itemsize
        with open(self.img_path, "rb") as f:
            for i, row in enumerate(range(y0, y1)):
                f.seek(row * self.row_stride + x0 * self.itemsize)
                buf = f.read(bytes_per_row)
                patch[i, :] = np.frombuffer(buf, dtype=self.dtype)

        # Normalize patch to float32 [0, 1]
        patch_f = patch.astype(np.float32)
        valid = patch_f[patch_f > 0]
        if len(valid) > 0:
            vmin = np.percentile(valid, 1)
            vmax = np.percentile(valid, 99)
            if vmax > vmin:
                return np.clip((patch_f - vmin) / (vmax - vmin), 0.0, 1.0)
        return patch_f / (np.max(patch_f) + 1e-6)

    def get_overview(self, target_max_dim: int = 2048) -> np.ndarray:
        """
        Builds a quick decimated thumbnail by seeking every step-th scan line.
        """
        step = max(1, max(self.lines, self.samples) // target_max_dim)
        sampled_rows = range(0, self.lines, step)
        overview_lines = len(sampled_rows)
        overview_samples = self.samples // step

        overview = np.empty((overview_lines, overview_samples), dtype=self.dtype)

        with open(self.img_path, "rb") as f:
            for i, row in enumerate(sampled_rows):
                f.seek(row * self.row_stride)
                buf = f.read(self.row_stride)
                full_row = np.frombuffer(buf, dtype=self.dtype)
                overview[i, :] = full_row[::step][:overview_samples]

        ov_f = overview.astype(np.float32)
        valid = ov_f[ov_f > 0]
        if len(valid) > 0:
            vmin = np.percentile(valid, 1)
            vmax = np.percentile(valid, 99)
            if vmax > vmin:
                return np.clip((ov_f - vmin) / (vmax - vmin), 0.0, 1.0)
        return ov_f / (np.max(ov_f) + 1e-6)
