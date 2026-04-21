from __future__ import annotations

from typing import Callable

import rospy
from sensor_msgs.msg import Image


class ImageInput:
    def __init__(self, topic: str, callback: Callable[[Image], None], queue_size: int = 1):
        self.topic = topic
        self.subscriber = rospy.Subscriber(topic, Image, callback, queue_size=queue_size, buff_size=2 ** 24)

