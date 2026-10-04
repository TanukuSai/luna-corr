"""
Base classes and data structures for image matchers.
"""
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np

@dataclass
class MatchResult:
    src_points: np.ndarray  # Shape (N, 2), (x, y) coordinates in source image
    ref_points: np.ndarray  # Shape (N, 2), (x, y) coordinates in reference image
    scores: np.ndarray      # Shape (N,), confidence / distance metric
    matcher_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.src_points)

    @property
    def is_empty(self) -> bool:
        return len(self.src_points) == 0

class BaseMatcher(ABC):
    """Abstract base class for all correspondence matchers."""

    @abstractmethod
    def match(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        src_mask: Optional[np.ndarray] = None,
        ref_mask: Optional[np.ndarray] = None
    ) -> MatchResult:
        """
        Finds correspondence between source and reference images.
        Both images should be 2D float32 [0, 1] arrays.
        """
        pass
