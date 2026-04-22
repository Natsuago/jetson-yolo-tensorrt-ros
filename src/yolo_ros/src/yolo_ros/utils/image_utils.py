from __future__ import annotations

from typing import Iterable, Optional, Tuple

import numpy as np

from yolo_ros.core.detection_result import DetectionResult


_PALETTE = (
    (255, 56, 56),
    (255, 157, 151),
    (255, 112, 31),
    (255, 178, 29),
    (207, 210, 49),
    (72, 249, 10),
    (146, 204, 23),
    (61, 219, 134),
    (26, 147, 52),
    (0, 212, 187),
    (44, 153, 168),
    (0, 194, 255),
    (52, 69, 147),
    (100, 115, 255),
    (0, 24, 236),
    (132, 56, 255),
    (82, 0, 133),
    (203, 56, 255),
    (255, 149, 200),
    (255, 55, 199),
)


def _class_color(class_id: int) -> Tuple[int, int, int]:
    color = _PALETTE[int(class_id) % len(_PALETTE)]
    return int(color[0]), int(color[1]), int(color[2])


def _draw_fps(cv2, image: np.ndarray, fps: Optional[float]) -> None:
    if fps is None:
        return
    label = f"FPS: {fps:.1f}"
    origin = (10, 30)
    cv2.putText(
        image,
        label,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )


def draw_detections(
    cv_image: np.ndarray,
    detections: Iterable[DetectionResult],
    fps: Optional[float] = None,
) -> np.ndarray:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV Python module cv2 is required for overlay publishing.") from exc

    output = cv_image.copy()
    for detection in detections:
        pt1 = (int(round(detection.xmin)), int(round(detection.ymin)))
        pt2 = (int(round(detection.xmax)), int(round(detection.ymax)))
        label = f"{detection.class_name} {detection.score:.2f}"
        color = _class_color(detection.class_id)
        cv2.rectangle(output, pt1, pt2, color, 2)

        text_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        text_x = max(0, pt1[0])
        text_y = max(text_size[1] + 4, pt1[1] - 6)
        bg_pt1 = (text_x, text_y - text_size[1] - 4)
        bg_pt2 = (text_x + text_size[0] + 4, text_y + baseline)
        cv2.rectangle(output, bg_pt1, bg_pt2, color, thickness=-1)
        cv2.putText(
            output,
            label,
            (text_x + 2, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    _draw_fps(cv2, output, fps)
    return output
