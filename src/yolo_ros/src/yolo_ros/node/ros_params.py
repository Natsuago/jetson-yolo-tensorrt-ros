from __future__ import annotations

from typing import Any, List

import rospy

from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.utils.yaml_utils import parse_bool


def _has_private(name: str) -> bool:
    return rospy.has_param(f"~{name}")


def _get_private(name: str, default: Any = None) -> Any:
    return rospy.get_param(f"~{name}", default)


def _parse_classes(value: Any) -> List[int]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    return [int(item) for item in value]


def load_profile_from_rosparams() -> ModelProfile:
    profile_path = str(_get_private("model_profile", "") or "")
    if not profile_path:
        raise ValueError("Private parameter ~model_profile is required.")

    profile = ModelProfile.from_file(profile_path)

    ros_overrides = {
        "image_topic": "image_topic",
        "camera_info_topic": "camera_info_topic",
        "detections_topic": "detections_topic",
        "overlay_topic": "overlay_topic",
        "publish_overlay": "publish_overlay",
        "queue_size": "queue_size",
    }
    for param_name, field_name in ros_overrides.items():
        if _has_private(param_name):
            value = _get_private(param_name)
            if field_name == "publish_overlay":
                value = parse_bool(value)
            if field_name == "queue_size":
                value = int(value)
            setattr(profile.ros, field_name, value)

    inference_overrides = {
        "conf": float,
        "iou": float,
        "max_det": int,
    }
    for param_name, caster in inference_overrides.items():
        if _has_private(param_name):
            setattr(profile.inference, param_name, caster(_get_private(param_name)))
    if _has_private("classes"):
        profile.inference.classes = _parse_classes(_get_private("classes"))

    return profile

