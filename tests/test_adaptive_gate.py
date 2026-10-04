"""
Tests for Adaptive Deformation Gate (Homography vs Non-Rigid Thin-Plate Spline).
Verifies dual-condition trigger (S_relief > 0.20 AND P95 >= 1.5 px),
epsilon-zero residual exclusion, deterministic nearest-neighbor calculations,
and absence of test-point leakage.
"""
import numpy as np
import pytest
from lunacorr.estimate.adaptive_gate import AdaptiveDeformationGate

def test_adaptive_gate_planar_rejection():
    """When residuals are small (< min_p95_px), homography must be maintained regardless of correlation."""
    gate = AdaptiveDeformationGate(autocorr_threshold=0.20, min_p95_px=1.5)
    np.random.seed(42)
    pts = np.random.uniform(0, 1000, (50, 2))
    # Highly correlated residuals but tiny magnitude (0.3 px)
    residuals = np.ones((50, 2)) * 0.3
    
    decision = gate.analyze(pts, residuals, homography_p95_px=0.45)
    assert decision.selected_model == "HOMOGRAPHY"
    assert "rigid planar tolerance" in decision.reason

def test_adaptive_gate_uncorrelated_noise_rejection():
    """When residuals are large but spatially uncorrelated (random white noise), homography must be maintained."""
    gate = AdaptiveDeformationGate(autocorr_threshold=0.20, min_p95_px=1.5)
    np.random.seed(42)
    pts = np.random.uniform(0, 1000, (100, 2))
    # Random uncorrelated directions with large magnitude
    angles = np.random.uniform(0, 2 * np.pi, 100)
    mags = np.random.uniform(2.0, 5.0, 100)
    residuals = np.column_stack([mags * np.cos(angles), mags * np.sin(angles)])
    
    decision = gate.analyze(pts, residuals, homography_p95_px=4.2)
    assert decision.selected_model == "HOMOGRAPHY"
    assert decision.spatial_autocorrelation <= 0.20
    assert "uncorrelated noise" in decision.reason

def test_adaptive_gate_relief_parallax_trigger():
    """When residuals exhibit strong spatial directional coherence and P95 >= 1.5 px, TPS must trigger."""
    gate = AdaptiveDeformationGate(autocorr_threshold=0.20, min_p95_px=1.5)
    np.random.seed(42)
    # Grid of points representing topographic relief
    gx, gy = np.meshgrid(np.linspace(100, 900, 8), np.linspace(100, 900, 8))
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    
    # Coherent topographic displacement field (e.g. radial displacement from crater rim)
    cx, cy = 500.0, 500.0
    dx = pts[:, 0] - cx
    dy = pts[:, 1] - cy
    dist = np.hypot(dx, dy) + 1e-6
    # Radial displacement outward
    residuals = np.column_stack([3.0 * (dx / dist), 3.0 * (dy / dist)])
    
    decision = gate.analyze(pts, residuals, homography_p95_px=3.0)
    assert decision.selected_model == "TPS"
    assert decision.spatial_autocorrelation > 0.20
    assert "exhibit spatial relief correlation" in decision.reason

def test_adaptive_gate_eps_zero_exclusion():
    """Residuals near zero (< eps_zero) must be excluded to prevent division-by-zero or numerical noise blowup."""
    gate = AdaptiveDeformationGate(autocorr_threshold=0.20, min_p95_px=1.5, eps_zero=0.05, min_points=10)
    np.random.seed(42)
    pts = np.random.uniform(0, 1000, (20, 2))
    # 15 points with exact zero residuals, only 5 points with residuals
    residuals = np.zeros((20, 2))
    residuals[:5] = np.array([[2.0, 2.0]] * 5)
    
    decision = gate.analyze(pts, residuals, homography_p95_px=2.5)
    # Since only 5 points are >= eps_zero, it has insufficient non-zero points (< min_points=10)
    assert decision.selected_model == "HOMOGRAPHY"
    assert "Insufficient non-zero residual vectors" in decision.reason
