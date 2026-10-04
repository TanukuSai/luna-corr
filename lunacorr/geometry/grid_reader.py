"""
ISRO Geometry Grid and Telemetry Reader for Chandrayaan-2 push-broom sensors.
Parses _g_grd_d18.csv and _d_img_d18.lbr files to map pixels to lunar body-fixed coordinates.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import csv
import numpy as np
from scipy.interpolate import RegularGridInterpolator

@dataclass
class GeometryFootprint:
    product_id: str
    min_lon: float
    max_lon: float
    min_lat: float
    max_lat: float
    corners: np.ndarray  # 4x2 array of (lon, lat)

    def intersects(self, other: "GeometryFootprint") -> bool:
        """Checks bounding box overlap in lunar coordinates."""
        return not (
            self.max_lon < other.min_lon or
            self.min_lon > other.max_lon or
            self.max_lat < other.min_lat or
            self.min_lat > other.max_lat
        )

    def overlap_bbox(self, other: "GeometryFootprint") -> Optional[Tuple[float, float, float, float]]:
        """Returns (min_lon, max_lon, min_lat, max_lat) of the intersection."""
        if not self.intersects(other):
            return None
        return (
            max(self.min_lon, other.min_lon),
            min(self.max_lon, other.max_lon),
            max(self.min_lat, other.min_lat),
            min(self.max_lat, other.max_lat)
        )

class ISROGeometryReader:
    """Parses ISRO Chandrayaan-2 geometry grids and attitude files."""

    @staticmethod
    def load_grid_csv(csv_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Reads Longitude, Latitude, Pixel, Scan columns from geometry CSV.
        """
        lons, lats, pixels, scans = [], [], [], []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)  # Longitude,Latitude,Pixel,Scan
            for row in reader:
                if len(row) >= 4:
                    lons.append(float(row[0]))
                    lats.append(float(row[1]))
                    pixels.append(float(row[2]))
                    scans.append(float(row[3]))

        return (
            np.array(lons, dtype=np.float32),
            np.array(lats, dtype=np.float32),
            np.array(pixels, dtype=np.float32),
            np.array(scans, dtype=np.float32)
        )

    @classmethod
    def get_footprint(cls, csv_path: Path) -> GeometryFootprint:
        """Extracts the spatial footprint of the product in lunar coordinates."""
        lons, lats, pixels, scans = cls.load_grid_csv(csv_path)
        
        # Identify the 4 corner points
        idx_tl = 0
        idx_tr = np.argmax(pixels[:100])
        idx_bl = len(pixels) - 100 + np.argmin(pixels[-100:])
        idx_br = len(pixels) - 1

        corners = np.array([
            [lons[idx_tl], lats[idx_tl]],
            [lons[idx_tr], lats[idx_tr]],
            [lons[idx_br], lats[idx_br]],
            [lons[idx_bl], lats[idx_bl]],
        ], dtype=np.float32)

        return GeometryFootprint(
            product_id=csv_path.stem.replace("_g_grd_d18", ""),
            min_lon=float(np.min(lons)),
            max_lon=float(np.max(lons)),
            min_lat=float(np.min(lats)),
            max_lat=float(np.max(lats)),
            corners=corners
        )
