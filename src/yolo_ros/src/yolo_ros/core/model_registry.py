from __future__ import annotations

from typing import Dict

from yolo_ros.core.exceptions import ProviderError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.providers.base_provider import BaseProvider
from yolo_ros.providers.ultralytics_provider import UltralyticsProvider
from yolo_ros.providers.yolov13_provider import Yolov13Provider
from yolo_ros.providers.yolov5_classic_provider import Yolov5ClassicProvider


def _providers() -> Dict[str, BaseProvider]:
    providers = [
        UltralyticsProvider(),
        Yolov5ClassicProvider(),
        Yolov13Provider(),
    ]
    return {provider.family: provider for provider in providers}


def get_provider(profile: ModelProfile) -> BaseProvider:
    providers = _providers()
    provider = providers.get(profile.model.family)
    if provider is None:
        supported = ", ".join(sorted(providers.keys()))
        raise ProviderError(
            f"Unsupported YOLO family={profile.model.family!r}. Supported families: {supported}."
        )
    provider.validate_profile(profile)
    return provider

