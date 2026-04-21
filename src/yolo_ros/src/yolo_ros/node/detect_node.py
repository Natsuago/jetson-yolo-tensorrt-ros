from __future__ import annotations

import threading

import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import CameraInfo, Image

from yolo_ros.core.exceptions import YoloRosError
from yolo_ros.core.model_profile import check_metadata_compatibility
from yolo_ros.core.model_registry import get_provider
from yolo_ros.node.ros_params import load_profile_from_rosparams
from yolo_ros.ros.image_input import ImageInput
from yolo_ros.tasks.detect_task import DetectTask


class YoloDetectNode:
    def __init__(self) -> None:
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.last_camera_info = None

        self.profile = load_profile_from_rosparams()
        check_metadata_compatibility(self.profile, rospy.logwarn)

        provider = get_provider(self.profile)
        status_note = provider.get_status_note()
        if status_note:
            rospy.logwarn(status_note)

        self.runner = provider.create_runner(self.profile)
        self.runner.load()
        self.task = DetectTask(self.profile, self.runner)

        subscribe_camera_info = bool(rospy.get_param("~subscribe_camera_info", True))
        if subscribe_camera_info and self.profile.ros.camera_info_topic:
            self.camera_info_sub = rospy.Subscriber(
                self.profile.ros.camera_info_topic,
                CameraInfo,
                self._camera_info_callback,
                queue_size=1,
            )
        else:
            self.camera_info_sub = None

        self.image_input = ImageInput(
            self.profile.ros.image_topic,
            self._image_callback,
            queue_size=self.profile.ros.queue_size,
        )

        rospy.loginfo(
            "YOLO detect node ready: image=%s detections=%s overlay=%s backend=%s model=%s",
            self.profile.ros.image_topic,
            self.profile.ros.detections_topic,
            self.profile.ros.overlay_topic if self.profile.ros.publish_overlay else "disabled",
            self.profile.model.backend,
            self.profile.model.path,
        )

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        self.last_camera_info = msg

    def _image_callback(self, msg: Image) -> None:
        if not self.lock.acquire(blocking=False):
            rospy.logwarn_throttle(5.0, "Dropping image because previous YOLO inference is still running.")
            return
        try:
            try:
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            except CvBridgeError as exc:
                rospy.logerr_throttle(2.0, "Failed to convert ROS Image to BGR OpenCV image: %s", exc)
                return
            self.task.process(cv_image, msg.header)
        except Exception as exc:
            rospy.logerr_throttle(2.0, "YOLO image callback failed: %s", exc)
        finally:
            self.lock.release()


def main() -> None:
    rospy.init_node("yolo_detect")
    try:
        YoloDetectNode()
    except (YoloRosError, ValueError, FileNotFoundError) as exc:
        rospy.logfatal("Failed to start yolo_ros detect node: %s", exc)
        rospy.signal_shutdown(str(exc))
        return
    rospy.spin()

