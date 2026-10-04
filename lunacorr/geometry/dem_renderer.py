"""
Physics-based Lunar DEM Lighting Renderer (Mode C).
Renders Digital Elevation Models (DEMs) under specific Sun angles using Lommel-Seeliger / Lunar-Lambert reflectance.
"""
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import cv2

class LunarDEMRenderer:
    """
    Simulates optical appearance of lunar terrain from digital elevation models (LOLA DEM or TMC-2 DEM).
    Eliminates cross-illumination divergence by rendering the reference DEM under the exact lighting
    of the source observation.
    """

    @staticmethod
    def render_lunar_lambert(
        dem_elevation_m: np.ndarray,
        pixel_scale_m: float,
        sun_azimuth_deg: float,
        sun_elevation_deg: float,
        weight_lommel_seeliger: float = 0.6,
        cast_shadows: bool = True
    ) -> np.ndarray:
        """
        Renders a synthetic lunar optical image from a DEM:
        mu0 = n . s (cosine of incidence angle)
        mu  = n . v (cosine of emission angle; v = [0, 0, 1] for nadir)
        Reflectance = mu0 * ((1 - w) + 2 * w / (mu0 + mu))
        """
        dem_f = dem_elevation_m.astype(np.float32)
        
        # 1. Surface normals from elevation gradients (dz/dx, dz/dy)
        gx = cv2.Sobel(dem_f, cv2.CV_32F, 1, 0, ksize=3) / (8.0 * pixel_scale_m)
        gy = cv2.Sobel(dem_f, cv2.CV_32F, 0, 1, ksize=3) / (8.0 * pixel_scale_m)

        norm = np.sqrt(gx**2 + gy**2 + 1.0)
        nx = -gx / norm
        ny = -gy / norm
        nz = 1.0 / norm

        # 2. Sun vector
        az_rad = np.deg2rad(sun_azimuth_deg)
        el_rad = np.deg2rad(sun_elevation_deg)
        sx = np.cos(el_rad) * np.sin(az_rad)
        sy = np.cos(el_rad) * np.cos(az_rad)
        sz = np.sin(el_rad)

        # 3. Incidence cosine mu0 and Nadir Emission cosine mu
        mu0 = nx * sx + ny * sy + nz * sz
        mu0 = np.clip(mu0, 0.0, 1.0)
        mu = nz  # Nadir viewing

        w = weight_lommel_seeliger
        # Lunar-Lambert combination
        denom = mu0 + mu + 1e-6
        reflectance = mu0 * ((1.0 - w) + 2.0 * w / denom)

        # 4. Ray-march shadows for low grazing sun elevations
        if cast_shadows and sun_elevation_deg < 35.0:
            shadow_mask = LunarDEMRenderer._cast_shadows(dem_f, pixel_scale_m, sx, sy, sz)
            reflectance[shadow_mask] *= 0.05  # Ambient starlight/earthshine only

        # Robust stretch to [0, 1]
        p1, p99 = np.percentile(reflectance, 1), np.percentile(reflectance, 99)
        if p99 > p1:
            render = np.clip((reflectance - p1) / (p99 - p1), 0.0, 1.0)
        else:
            render = np.clip(reflectance, 0.0, 1.0)

        return render.astype(np.float32)

    @staticmethod
    def _cast_shadows(
        dem: np.ndarray,
        pixel_scale_m: float,
        sx: float,
        sy: float,
        sz: float,
        max_steps: int = 50
    ) -> np.ndarray:
        """
        Directional ray-marching across DEM grid along Sun azimuth to identify occluded terrain.
        """
        h, w = dem.shape
        tan_el = sz / (np.sqrt(sx**2 + sy**2) + 1e-6)
        
        step_dist_m = pixel_scale_m
        dx = -sx * step_dist_m / pixel_scale_m
        dy = -sy * step_dist_m / pixel_scale_m
        dz = step_dist_m * tan_el

        shadow = np.zeros((h, w), dtype=bool)
        ray_h = dem.copy()

        for step in range(1, max_steps):
            shift_x = int(round(step * dx))
            shift_y = int(round(step * dy))
            
            # Boundary checks
            if abs(shift_x) >= w or abs(shift_y) >= h:
                break

            # Roll elevation up along sun vector
            M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
            shifted_dem = cv2.warpAffine(dem, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            ray_elev = shifted_dem + step * dz

            shadow |= (ray_elev > dem)

        return shadow
