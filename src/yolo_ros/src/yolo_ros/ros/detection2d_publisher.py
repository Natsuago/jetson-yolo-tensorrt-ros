from __future__ import annotations

from typing import Iterable

import rospy
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

from yolo_ros.core.detection_result import DetectionResult


class Detection2DPublisher:
    def __init__(self, topic: str, queue_size: int = 1):
        self.publisher = rospy.Publisher(topic, Detection2DArray, queue_size=queue_size)

    def publish(self, detections: Iterable[DetectionResult], header) -> None:
        msg = Detection2DArray()
        msg.header = header
        for result in detections:
            msg.detections.append(self._to_detection_msg(result, header))
        self.publisher.publish(msg)

    @staticmethod
    def _to_detection_msg(result: DetectionResult, header) -> Detection2D:
        detection = Detection2D()
        detection.header = header
        detection.bbox.center.x = result.center_x
        detection.bbox.center.y = result.center_y
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = result.width
        detection.bbox.size_y = result.height

        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.id = int(result.class_id)
        hypothesis.hypothesis.score = float(result.score)
        detection.results.append(hypothesis)
        return detection

