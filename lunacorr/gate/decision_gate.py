"""
Quality gate implementing mandatory scientific abstention logic.
Refuses registration and produces explicit diagnostic codes when confidence or distribution criteria are not met.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class GateDecision:
    accepted: bool
    status: str  # "ACCEPTED" or "ABSTAINED"
    reason_codes: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    uncalibrated_quality_score: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)

class QualityGate:
    """
    Evaluates registration metrics against objective quality thresholds.
    Abstains if any criterion fails, preventing erroneous scientific alignments.

    Operational Acceptance Thresholds:
      - min_inliers: 20 (Unified with statistical reporting threshold N >= 20)
      - min_inlier_ratio: 0.15 (15% consensus required)
      - min_occupied_ratio: 0.30 (30% spatial grid coverage required)
      - max_empty_circle: 0.45 (Max normalized empty radius)
      - max_p95_residual_px: 4.0 px (Upper tolerance on P95 residual)
    """

    def __init__(
        self,
        min_inliers: int = 20,
        min_inlier_ratio: float = 0.15,
        min_occupied_ratio: float = 0.30,
        max_empty_circle: float = 0.45,
        max_p95_residual_px: float = 4.0
    ):
        self.min_inliers = min_inliers
        self.min_inlier_ratio = min_inlier_ratio
        self.min_occupied_ratio = min_occupied_ratio
        self.max_empty_circle = max_empty_circle
        self.max_p95_residual_px = max_p95_residual_px

    def evaluate(
        self,
        inlier_count: int,
        inlier_ratio: float,
        occupied_ratio: float,
        largest_empty_circle: float,
        p95_residual_px: float,
        entropy: float = 0.0
    ) -> GateDecision:
        reasons = []

        if inlier_count < self.min_inliers:
            reasons.append("LOW_INLIERS")

        if inlier_ratio < self.min_inlier_ratio:
            reasons.append("LOW_INLIER_RATIO")

        if occupied_ratio < self.min_occupied_ratio:
            reasons.append("LOW_COVERAGE")

        if largest_empty_circle > self.max_empty_circle:
            reasons.append("LARGE_HOLE")

        if p95_residual_px > self.max_p95_residual_px:
            reasons.append("HIGH_RESIDUAL")

        accepted = len(reasons) == 0

        # Uncalibrated Engineering Quality Composite Index [0, 1]
        # Formula: 0.4 * min(1.0, N / 50.0) + 0.3 * occupied_ratio + 0.3 * max(0.0, 1.0 - p95 / max_p95)
        # Note: This is an empirical composite score, NOT a calibrated Bayesian posterior probability.
        c_inl = min(1.0, inlier_count / 50.0)
        c_cov = occupied_ratio
        c_res = max(0.0, 1.0 - p95_residual_px / self.max_p95_residual_px)
        composite = float(0.4 * c_inl + 0.3 * c_cov + 0.3 * c_res) if accepted else 0.0
        score = round(composite, 3)

        return GateDecision(
            accepted=accepted,
            status="ACCEPTED" if accepted else "ABSTAINED",
            reason_codes=reasons,
            quality_score=score,
            uncalibrated_quality_score=score,
            metrics={
                "inlier_count": inlier_count,
                "inlier_ratio": round(inlier_ratio, 3),
                "occupied_ratio": round(occupied_ratio, 3),
                "largest_empty_circle": round(largest_empty_circle, 3),
                "p95_residual_px": round(p95_residual_px, 2),
                "entropy": round(entropy, 3)
            }
        )
