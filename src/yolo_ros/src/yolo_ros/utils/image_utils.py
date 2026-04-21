from __future__ import annotations

from typing import Iterable

import numpy as np

from yolo_ros.core.detection_result import DetectionResult


def draw_detections(cv_image: np.ndarray, detections: Iterable[DetectionResult]) -> np.ndarray:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV Python module cv2 is required for overlay publishing.") from exc

    output = cv_image.copy()
    for detection in detections:
        pt1 = (int(round(detection.xmin)), int(round(detection.ymin)))
        pt2 = (int(round(detection.xmax)), int(round(detection.ymax)))
        label = f"{detection.class_name} {detection.score:.2f}"
        cv2.rectangle(output, pt1, pt2, (0, 180, 255), 2)
        text_origin = (pt1[0], max(0, pt1[1] - 6))
        cv2.putText(
            output,
            label,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 180, 255),
            1,
            cv2.LINE_AA,
        )
    return output

