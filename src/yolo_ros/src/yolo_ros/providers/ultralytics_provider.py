from __future__ import annotations

from typing import Sequence

from yolo_ros.core.exceptions import ProviderError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.providers.base_provider import BaseProvider
from yolo_ros.runners.base_runner import BaseRunner
from yolo_ros.runners.ultralytics_runner import UltralyticsRunner


class UltralyticsProvider(BaseProvider):
    family = "ultralytics"

    def supported_versions(self) -> Sequence[str]:
        return ("8", "11", "12", "26")

    def supported_backends(self) -> Sequence[str]:
        return ("pt", "onnx", "engine")

    def supported_tasks(self) -> Sequence[str]:
        return ("detect",)

    def validate_profile(self, profile: ModelProfile) -> None:
        if profile.model.family != self.family:
            raise ProviderError(f"UltralyticsProvider cannot handle family={profile.model.family!r}.")
        if profile.model.version not in self.supported_versions():
            raise ProviderError(
                f"Unsupported Ultralytics YOLO version={profile.model.version!r}; "
                f"supported: {', '.join(self.supported_versions())}."
            )
        if profile.model.backend not in self.supported_backends():
            raise ProviderError(f"Unsupported backend={profile.model.backend!r} for UltralyticsProvider.")
        if profile.model.task not in self.supported_tasks():
            raise ProviderError("Only task=detect is implemented for UltralyticsProvider.")

    def create_runner(self, profile: ModelProfile) -> BaseRunner:
        self.validate_profile(profile)
        return UltralyticsRunner(profile)

