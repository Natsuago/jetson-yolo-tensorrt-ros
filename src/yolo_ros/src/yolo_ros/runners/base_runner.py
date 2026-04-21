from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

import numpy as np

from yolo_ros.core.detection_result import DetectionResult


class BaseRunner(ABC):
    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        cv_image: np.ndarray,
        conf: float,
        iou: float,
        imgsz,
        classes: Optional[Sequence[int]],
        max_det: int,
    ) -> List[DetectionResult]:
        raise NotImplementedError

