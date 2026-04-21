from __future__ import annotations

from typing import Sequence

from yolo_ros.core.exceptions import ProviderError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.providers.base_provider import BaseProvider
from yolo_ros.runners.base_runner import BaseRunner
from yolo_ros.runners.ultralytics_runner import UltralyticsRunner


class Yolov13Provider(BaseProvider):
    family = "yolov13"

    def supported_versions(self) -> Sequence[str]:
        return ("13",)

    def supported_backends(self) -> Sequence[str]:
        return ("pt", "onnx", "engine")

    def supported_tasks(self) -> Sequence[str]:
        return ("detect",)

    def validate_profile(self, profile: ModelProfile) -> None:
        if profile.model.family != self.family:
            raise ProviderError(f"Yolov13Provider cannot handle family={profile.model.family!r}.")
        if profile.model.version not in self.supported_versions():
            raise ProviderError("YOLOv13 provider only supports version='13'.")
        if profile.model.backend not in self.supported_backends():
            raise ProviderError(f"Unsupported backend={profile.model.backend!r} for YOLOv13.")
        if profile.model.task not in self.supported_tasks():
            raise ProviderError("Only task=detect is implemented for YOLOv13.")

    def create_runner(self, profile: ModelProfile) -> BaseRunner:
        self.validate_profile(profile)
        return UltralyticsRunner(profile, experimental_note=self.get_status_note())

    def get_status_note(self) -> str:
        return (
            "YOLOv13 support is experimental. Install and validate the iMoonLab/yolov13 "
            "ultralytics-style runtime before using pt/onnx/engine models."
        )

