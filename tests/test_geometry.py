import numpy as np
import pytest
from lunacorr.estimate.robust import RobustEstimator
from lunacorr.estimate.nonrigid import ElasticTransformer

def test_homography_estimation():
    np.random.seed(42)
    src_pts = np.random.uniform(50, 450, (100, 2)).astype(np.float32)
    # Synthetic affine transformation
    theta = np.deg2rad(5.0)
    R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    t = np.array([12.5, -8.3])
    ref_pts = (src_pts @ R.T) + t

    # Add 10 outliers
    ref_pts[:10] += np.random.uniform(50, 100, (10, 2))

    estimator = RobustEstimator(method="MAGSAC", reproj_threshold_px=2.0)
    result = estimator.estimate(src_pts, ref_pts, model_type="HOMOGRAPHY")

    assert result.inlier_count >= 85
    assert result.inlier_mask[:10].sum() == 0  # All 10 outliers rejected

def test_elastic_tps_fit():
    np.random.seed(42)
    grid_x, grid_y = np.meshgrid(np.linspace(0, 500, 10), np.linspace(0, 500, 10))
    src = np.column_stack([grid_x.ravel(), grid_y.ravel()]).astype(np.float32)
    # Non-rigid bump distortion
    disp_x = 5.0 * np.sin(src[:, 0] / 100.0)
    disp_y = 5.0 * np.cos(src[:, 1] / 100.0)
    ref = src + np.column_stack([disp_x, disp_y])

    transformer = ElasticTransformer(smoothing=0.1)
    res = transformer.fit(src, ref)

    pred = src + res.rbf_model(src)
    residuals = np.linalg.norm(ref - pred, axis=1)
    assert np.mean(residuals) < 0.5  # Sub-pixel reconstruction on non-rigid field
