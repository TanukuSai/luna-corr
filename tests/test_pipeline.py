import numpy as np
import pytest
from lunacorr.represent.preprocessor import RepresentationLayer
from lunacorr.matchers.classical import SIFTMatcher
from lunacorr.selection.soft_utility import SoftSpatialUtilitySelector

def test_local_contrast_normalization():
    img = np.random.uniform(0.1, 0.9, (256, 256)).astype(np.float32)
    # Add severe illumination gradient
    grad = np.linspace(0, 1, 256)[:, None].astype(np.float32)
    img_uneven = np.clip(img * grad, 0, 1)

    norm = RepresentationLayer.local_contrast_normalization(img_uneven, ksize=31)
    assert norm.shape == (256, 256)
    assert not np.isnan(norm).any()
    assert norm.min() >= 0.0 and norm.max() <= 1.0

def test_sift_matcher():
    img = np.zeros((300, 300), dtype=np.float32)
    # Draw geometric shapes to match
    img[50:100, 50:100] = 1.0
    img[150:220, 180:250] = 0.8
    img[70:90, 170:230] = 0.6

    matcher = SIFTMatcher(n_features=500, root_sift=True)
    matches = matcher.match(img, img)

    assert len(matches.src_points) > 0
    assert len(matches.src_points) == len(matches.ref_points)

def test_soft_spatial_utility_selection():
    pts = np.random.uniform(10, 490, (200, 2)).astype(np.float32)
    scores = np.random.uniform(0.5, 1.0, 200).astype(np.float32)
    residuals = np.random.uniform(0.1, 1.5, 200).astype(np.float32)

    selector = SoftSpatialUtilitySelector(grid_size=(4, 4), k_max_per_cell=5)
    selected = selector.select(pts, scores, residuals, image_shape=(500, 500))

    assert len(selected.selected_indices) <= 4 * 4 * 5
    assert len(selected.selected_indices) > 0
