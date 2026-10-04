"""
Transitive Multi-Modal Sensor Ladder (OHRC -> TMC-2 -> IIRS).
Bridges the 300x resolution and radiometric gap by using TMC-2 as an intermediate anchor.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

from .inference import LunarRegistrationPipeline, RegistrationOutput

@dataclass
class LadderRegistrationOutput:
    status: str
    transitive_matrix: Optional[np.ndarray]
    step1_ohrc_to_tmc2: RegistrationOutput
    step2_tmc2_to_iirs: RegistrationOutput
    confidence: float

class TransitiveSensorLadder:
    """
    Solves the extreme 300x scale gap between OHRC (0.25m) and IIRS (80m)
    by chaining registration through TMC-2 (5m):
    T_{OHRC -> IIRS} = T_{TMC2 -> IIRS} @ T_{OHRC -> TMC2}
    """

    def __init__(self, pipeline: Optional[LunarRegistrationPipeline] = None):
        self.pipeline = pipeline or LunarRegistrationPipeline()

    def register_ladder(
        self,
        ohrc_path: Path,
        tmc2_path: Path,
        iirs_path: Path,
        output_dir: Optional[Path] = None
    ) -> LadderRegistrationOutput:
        print("[Sensor Ladder] Step 1: Aligning OHRC (0.25m) to TMC-2 (5m)...")
        out1 = self.pipeline.run(ohrc_path, tmc2_path)

        if not out1.decision.accepted or out1.estimation is None:
            return LadderRegistrationOutput(
                status="FAILED_AT_STEP_1",
                transitive_matrix=None,
                step1_ohrc_to_tmc2=out1,
                step2_tmc2_to_iirs=out1,
                confidence=0.0
            )

        print("[Sensor Ladder] Step 2: Aligning TMC-2 (5m) to IIRS (80m)...")
        out2 = self.pipeline.run(tmc2_path, iirs_path)

        if not out2.decision.accepted or out2.estimation is None:
            return LadderRegistrationOutput(
                status="FAILED_AT_STEP_2",
                transitive_matrix=None,
                step1_ohrc_to_tmc2=out1,
                step2_tmc2_to_iirs=out2,
                confidence=0.0
            )

        # Compose transitive homographies: T_composite = T2 @ T1
        H1 = out1.estimation.matrix
        H2 = out2.estimation.matrix
        H_transitive = H2 @ H1
        # Normalize
        H_transitive /= (H_transitive[2, 2] + 1e-9)

        composite_conf = out1.decision.quality_score * out2.decision.quality_score

        print(f"[Sensor Ladder] Transitive Alignment Success! Combined Quality Score: {composite_conf:.3f}")

        return LadderRegistrationOutput(
            status="ACCEPTED",
            transitive_matrix=H_transitive,
            step1_ohrc_to_tmc2=out1,
            step2_tmc2_to_iirs=out2,
            confidence=composite_conf
        )
