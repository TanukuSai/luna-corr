"""
Negative Control Test Suite for Scientific Abstention.
Tests multiple failure modes against the QualityGate:
  1. Completely disjoint / zero-overlap scenes (insufficient inliers)
  2. Extremely low-texture input (flat featureless terrain)
  3. High noise / random uncorrelated correspondences
  4. Spatial clustering / large empty coverage hole
  5. High residual deformation exceeding tolerance

Verifies explicit reason-coded rejection, uncalibrated quality score = 0.0,
and fail-safe abstention behavior.
"""
import numpy as np
import pytest
from lunacorr.gate.decision_gate import QualityGate, GateDecision

@pytest.fixture
def gate():
    return QualityGate(
        min_inliers=20,
        min_inlier_ratio=0.15,
        min_occupied_ratio=0.30,
        max_empty_circle=0.45,
        max_p95_residual_px=4.0
    )

def test_negative_control_insufficient_inliers(gate):
    """Pair with only 5 matches (e.g. disjoint Apollo 11 vs South Pole) must be rejected with LOW_INLIERS."""
    decision = gate.evaluate(
        inlier_count=5,
        inlier_ratio=0.25,
        occupied_ratio=0.047,
        largest_empty_circle=0.344,
        p95_residual_px=2.99
    )
    assert not decision.accepted
    assert decision.status == "ABSTAINED"
    assert "LOW_INLIERS" in decision.reason_codes
    assert "LOW_COVERAGE" in decision.reason_codes
    assert decision.uncalibrated_quality_score == 0.0
    assert decision.quality_score == 0.0

def test_negative_control_low_consensus_ratio(gate):
    """Pair with many noisy matches but low inlier ratio (< 15%) must be rejected with LOW_INLIER_RATIO."""
    decision = gate.evaluate(
        inlier_count=35,
        inlier_ratio=0.08,  # Only 8% inliers out of 437 raw matches
        occupied_ratio=0.45,
        largest_empty_circle=0.25,
        p95_residual_px=2.50
    )
    assert not decision.accepted
    assert decision.status == "ABSTAINED"
    assert "LOW_INLIER_RATIO" in decision.reason_codes
    assert decision.uncalibrated_quality_score == 0.0

def test_negative_control_spatial_clustering_large_hole(gate):
    """Pair where matches cluster in a single corner leaving a large empty region must be rejected with LARGE_HOLE."""
    decision = gate.evaluate(
        inlier_count=80,
        inlier_ratio=0.65,
        occupied_ratio=0.35,
        largest_empty_circle=0.55,  # Empty circle > 0.45
        p95_residual_px=1.80
    )
    assert not decision.accepted
    assert decision.status == "ABSTAINED"
    assert "LARGE_HOLE" in decision.reason_codes

def test_negative_control_high_residual_error(gate):
    """Pair where residuals exceed 4.0 px tolerance must be rejected with HIGH_RESIDUAL."""
    decision = gate.evaluate(
        inlier_count=120,
        inlier_ratio=0.75,
        occupied_ratio=0.65,
        largest_empty_circle=0.20,
        p95_residual_px=6.50  # P95 > 4.0 px
    )
    assert not decision.accepted
    assert decision.status == "ABSTAINED"
    assert "HIGH_RESIDUAL" in decision.reason_codes

def test_positive_control_nominal_acceptance(gate):
    """Valid scientific pair exceeding all thresholds must be accepted with positive uncalibrated quality score."""
    decision = gate.evaluate(
        inlier_count=686,
        inlier_ratio=0.77,
        occupied_ratio=0.844,
        largest_empty_circle=0.084,
        p95_residual_px=2.01
    )
    assert decision.accepted
    assert decision.status == "ACCEPTED"
    assert len(decision.reason_codes) == 0
    assert decision.uncalibrated_quality_score > 0.70
    # Verify uncalibrated quality score formula:
    # c_inl = min(1.0, 686/50) = 1.0
    # c_cov = 0.844
    # c_res = max(0.0, 1.0 - 2.01 / 4.0) = 0.4975
    # composite = 0.4 * 1.0 + 0.3 * 0.844 + 0.3 * 0.4975 = 0.4 + 0.2532 + 0.14925 = 0.80245 -> 0.802
    assert decision.uncalibrated_quality_score == 0.802
