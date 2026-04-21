from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from yolo_ros.core.detection_result import DetectionResult
from yolo_ros.core.exceptions import RunnerError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.runners.base_runner import BaseRunner
from yolo_ros.utils.class_names import class_name_for, load_class_names, normalize_names


def _to_numpy(value) -> np.ndarray:
    if value is None:
        return np.asarray([])
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return value.numpy()
    return np.asarray(value)


class UltralyticsRunner(BaseRunner):
    def __init__(self, profile: ModelProfile, experimental_note: str = ""):
        self.profile = profile
        self.experimental_note = experimental_note
        self.model = None
        self.class_names = load_class_names(profile.model.class_names)

    def load(self) -> None:
        model_path = Path(self.profile.model.path).expanduser()
        if model_path.is_absolute() and not model_path.exists():
            raise RunnerError(
                f"Model file not found: {model_path}. Update model.path in {self.profile.source_path or 'the profile'}."
            )

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            note = f" {self.experimental_note}" if self.experimental_note else ""
            raise RunnerError(
                "Python package 'ultralytics' is required for UltralyticsProvider. "
                f"Install it with: pip3 install ultralytics.{note}"
            ) from exc

        try:
            self.model = YOLO(str(model_path))
        except Exception as exc:
            note = f" {self.experimental_note}" if self.experimental_note else ""
            raise RunnerError(f"Failed to load Ultralytics model {model_path}.{note} Error: {exc}") from exc

    def predict(
        self,
        cv_image: np.ndarray,
        conf: float,
        iou: float,
        imgsz,
        classes: Optional[Sequence[int]],
        max_det: int,
    ) -> List[DetectionResult]:
        if self.model is None:
            raise RunnerError("UltralyticsRunner.load() must be called before predict().")

        class_filter = None if not classes else [int(value) for value in classes]
        try:
            results = self.model.predict(
                source=cv_image,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                classes=class_filter,
                max_det=max_det,
                verbose=False,
            )
        except Exception as exc:
            raise RunnerError(f"Ultralytics predict() failed: {exc}") from exc

        detections: List[DetectionResult] = []
        for result in results:
            names = normalize_names(getattr(result, "names", None)) or self.class_names
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            xyxy = _to_numpy(getattr(boxes, "xyxy", None))
            scores = _to_numpy(getattr(boxes, "conf", None))
            class_ids = _to_numpy(getattr(boxes, "cls", None))
            if xyxy.size == 0:
                continue
            for coords, score, class_id in zip(xyxy, scores, class_ids):
                cid = int(class_id)
                detections.append(
                    DetectionResult(
                        class_id=cid,
                        class_name=class_name_for(cid, names),
                        score=float(score),
                        xmin=float(coords[0]),
                        ymin=float(coords[1]),
                        xmax=float(coords[2]),
                        ymax=float(coords[3]),
                    )
                )
        return detections
