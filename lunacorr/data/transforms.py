"""
Lunar-specific geometric and photometric augmentations for training and G0 benchmarking.
"""
from typing import Tuple, Dict, Any, Optional
import numpy as np
import cv2

class LunarAugmentor:
    """Generates realistic synthetic pairs under varying viewpoint and illumination."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def apply_illumination_simulation(
        self,
        img: np.ndarray,
        sun_azimuth_deg: float,
        sun_elevation_deg: float,
        shadow_intensity: float = 0.8
    ) -> np.ndarray:
        """
        Simulates directional shading and moving shadows based on Sun azimuth and elevation.
        Uses image gradients as pseudo-topography normals.
        """
        img_f = img.astype(np.float32)
        # Compute pseudo-surface normals using Sobel
        gx = cv2.Sobel(img_f, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(img_f, cv2.CV_32F, 0, 1, ksize=3)
        
        # Sun direction vector
        az_rad = np.deg2rad(sun_azimuth_deg)
        el_rad = np.deg2rad(sun_elevation_deg)
        sx = np.cos(el_rad) * np.sin(az_rad)
        sy = np.cos(el_rad) * np.cos(az_rad)
        sz = np.sin(el_rad)

        # Lambertian shading term mu0 = (n . s)
        # Assuming surface normal is approx (-gx, -gy, 1) normalized
        norm = np.sqrt(gx**2 + gy**2 + 1.0)
        shading = (-gx * sx - gy * sy + sz) / norm
        shading = np.clip((shading + 1.0) / 2.0, 0.05, 1.0)

        # Modulate original reflectance
        illuminated = img * (0.4 + 0.6 * shading)

        # Grazing angle shadow simulation if elevation is low
        if sun_elevation_deg < 25.0:
            shadow_thresh = np.percentile(illuminated, 20.0 * (1.0 - sun_elevation_deg / 25.0))
            shadow_mask = illuminated < shadow_thresh
            illuminated[shadow_mask] *= (1.0 - shadow_intensity)

        return np.clip(illuminated, 0.0, 1.0).astype(np.float32)

    def generate_pair(
        self,
        img: np.ndarray,
        max_rotation_deg: float = 30.0,
        scale_range: Tuple[float, float] = (0.7, 1.4),
        max_perspective: float = 0.1,
        simulate_illumination: bool = True
    ) -> Dict[str, Any]:
        """
        Creates a synthetic pair (src, ref) from a single lunar image with exact ground truth.
        """
        h, w = img.shape[:2]
        
        # 1. Random Homography
        angle = np.deg2rad(self.rng.uniform(-max_rotation_deg, max_rotation_deg))
        scale = np.exp(self.rng.uniform(np.log(scale_range[0]), np.log(scale_range[1])))
        
        # Affine components
        R = scale * np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        center = np.array([w / 2.0, h / 2.0])
        t = self.rng.uniform(-0.1, 0.1, size=2) * np.array([w, h])
        offset = center - R @ center + t

        H = np.eye(3, dtype=np.float32)
        H[:2, :2] = R
        H[:2, 2] = offset

        # Add mild perspective distortion
        H[2, 0] = self.rng.uniform(-max_perspective, max_perspective) / w
        H[2, 1] = self.rng.uniform(-max_perspective, max_perspective) / h

        # Warp image
        warped = cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        mask = cv2.warpPerspective(np.ones_like(img, dtype=np.uint8), H, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0

        # 2. Photometric augmentations
        ref_img = img.copy()
        src_img = warped.copy()

        if simulate_illumination:
            # Different sun angles for source vs reference
            ref_az = self.rng.uniform(0, 360)
            ref_el = self.rng.uniform(15, 60)
            src_az = (ref_az + self.rng.uniform(30, 180)) % 360
            src_el = self.rng.uniform(10, 50)

            ref_img = self.apply_illumination_simulation(ref_img, ref_az, ref_el)
            src_img = self.apply_illumination_simulation(src_img, src_az, src_el)

        # Gamma and sensor noise
        gamma = self.rng.uniform(0.7, 1.4)
        src_img = np.clip(src_img ** gamma, 0.0, 1.0)
        
        noise_sigma = self.rng.uniform(0.005, 0.02)
        noise = self.rng.normal(0, noise_sigma, src_img.shape).astype(np.float32)
        src_img = np.clip(src_img + noise, 0.0, 1.0)

        return {
            "source": src_img,
            "reference": ref_img,
            "homography": H,
            "valid_mask": mask
        }
