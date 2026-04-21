from __future__ import annotations

from typing import Optional

import numpy as np

from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.ros.detection2d_publisher import Detection2DPublisher
from yolo_ros.ros.overlay_publisher import OverlayPublisher
from yolo_ros.runners.base_runner import BaseRunner


class DetectTask:
    def __init__(self, profile: ModelProfile, runner: BaseRunner):
        self.profile = profile
        self.runner = runner
        self.detection_publisher = Detection2DPublisher(
            profile.ros.detections_topic,
            queue_size=profile.ros.queue_size,
        )
        self.overlay_publisher: Optional[OverlayPublisher] = None
        if profile.ros.publish_overlay:
            self.overlay_publisher = OverlayPublisher(
                profile.ros.overlay_topic,
                queue_size=profile.ros.queue_size,
            )

    def process(self, cv_image: np.ndarray, header) -> None:
        inference = self.profile.inference
        detections = self.runner.predict(
            cv_image=cv_image,
            conf=inference.conf,
            iou=inference.iou,
            imgsz=self.profile.model.imgsz,
            classes=inference.classes,
            max_det=inference.max_det,
        )
        self.detection_publisher.publish(detections, header)
        if self.overlay_publisher is not None:
            self.overlay_publisher.publish(cv_image, detections, header)

