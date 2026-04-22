from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

from yolo_ros.core.detection_result import DetectionResult
from yolo_ros.utils.image_utils import draw_detections


class OverlayPublisher:
    def __init__(self, topic: str, queue_size: int = 1):
        self.publisher = rospy.Publisher(topic, Image, queue_size=queue_size)
        self.bridge = CvBridge()

    def publish(
        self,
        cv_image: np.ndarray,
        detections: Iterable[DetectionResult],
        header,
        fps: Optional[float] = None,
    ) -> None:
        overlay = draw_detections(cv_image, detections, fps=fps)
        msg = self.bridge.cv2_to_imgmsg(overlay, encoding="bgr8")
        msg.header = header
        self.publisher.publish(msg)
