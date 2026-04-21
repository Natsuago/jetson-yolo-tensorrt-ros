from __future__ import annotations

from typing import Sequence

from yolo_ros.core.exceptions import ProviderError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.providers.base_provider import BaseProvider
from yolo_ros.runners.base_runner import BaseRunner
from yolo_ros.runners.yolov5_classic_runner import Yolov5ClassicRunner


class Yolov5ClassicProvider(BaseProvider):
    family = "yolov5_classic"

    def supported_versions(self) -> Sequence[str]:
        return ("5",)

    def supported_backends(self) -> Sequence[str]:
        return ("pt", "onnx", "engine")

    def supported_tasks(self) -> Sequence[str]:
        return ("detect",)

    def validate_profile(self, profile: ModelProfile) -> None:
        if profile.model.family != self.family:
            raise ProviderError(f"Yolov5ClassicProvider cannot handle family={profile.model.family!r}.")
        if profile.model.version not in self.supported_versions():
            raise ProviderError("YOLOv5 classic provider only supports version='5'.")
        if profile.model.backend not in self.supported_backends():
            raise ProviderError(f"Unsupported backend={profile.model.backend!r} for YOLOv5 classic.")
        if profile.model.task not in self.supported_tasks():
            raise ProviderError("Only task=detect is implemented for YOLOv5 classic.")

    def create_runner(self, profile: ModelProfile) -> BaseRunner:
        self.validate_profile(profile)
        return Yolov5ClassicRunner(profile)

    def get_status_note(self) -> str:
        return (
            "YOLOv5 classic requires an external ultralytics/yolov5 clone. "
            "Set external.yolov5_repo in the model profile."
        )

