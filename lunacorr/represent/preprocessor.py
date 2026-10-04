"""
Representation layers for illumination and radiometric invariance.
Includes local normalization, gradient orientation modulo 180, and phase congruency approximations.
"""
from typing import Tuple
import numpy as np
import cv2

class RepresentationLayer:
    """Transforms raw lunar reflectance into illumination-robust representations."""

    @staticmethod
    def local_contrast_normalization(img: np.ndarray, ksize: int = 31, eps: float = 1e-4) -> np.ndarray:
        """
        Removes low-frequency illumination gradients:
        J = (I - mu) / (sigma + eps)
        """
        img_f = img.astype(np.float32)
        mu = cv2.GaussianBlur(img_f, (ksize, ksize), 0)
        sq_diff = (img_f - mu) ** 2
        sigma = np.sqrt(cv2.GaussianBlur(sq_diff, (ksize, ksize), 0))
        norm = (img_f - mu) / (sigma + eps)
        # Robust stretch to [0, 1]
        p2, p98 = np.percentile(norm, 2), np.percentile(norm, 98)
        if p98 > p2:
            norm = np.clip((norm - p2) / (p98 - p2), 0.0, 1.0)
        else:
            norm = np.clip(norm, 0.0, 1.0)
        return norm.astype(np.float32)

    @staticmethod
    def gradient_orientation_map(img: np.ndarray, ksize: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes gradient magnitude and orientation modulo 180 degrees.
        Modulo 180 degrees suppresses contrast/shading inversion across opposite Sun angles.
        """
        gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=ksize)
        gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=ksize)
        mag = np.sqrt(gx**2 + gy**2)
        
        # Angles in degrees [0, 360) -> modulo 180 -> [0, 180)
        angle = (np.rad2deg(np.arctan2(gy, gx)) + 360.0) % 180.0
        angle_norm = (angle / 180.0).astype(np.float32)
        
        # Normalize magnitude
        p98 = np.percentile(mag, 98)
        if p98 > 0:
            mag_norm = np.clip(mag / p98, 0.0, 1.0).astype(np.float32)
        else:
            mag_norm = mag.astype(np.float32)

        return mag_norm, angle_norm

    @staticmethod
    def bandpass_structural_features(img: np.ndarray, low_sigma: float = 1.0, high_sigma: float = 8.0) -> np.ndarray:
        """
        Difference of Gaussians (DoG) bandpass filter highlighting lunar craters, rims, and boulder textures
        while rejecting macroscopic illumination ramps and sensor high-frequency noise.
        """
        g_low = cv2.GaussianBlur(img, (0, 0), low_sigma)
        g_high = cv2.GaussianBlur(img, (0, 0), high_sigma)
        dog = g_low - g_high
        
        # Scale to [0, 1]
        p1, p99 = np.percentile(dog, 1), np.percentile(dog, 99)
        if p99 > p1:
            dog_norm = np.clip((dog - p1) / (p99 - p1), 0.0, 1.0)
        else:
            dog_norm = np.clip(dog, 0.0, 1.0)
        return dog_norm.astype(np.float32)
