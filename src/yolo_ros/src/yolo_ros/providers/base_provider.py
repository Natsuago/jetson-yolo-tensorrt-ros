from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.runners.base_runner import BaseRunner


class BaseProvider(ABC):
    family: str = ""

    @abstractmethod
    def validate_profile(self, profile: ModelProfile) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_runner(self, profile: ModelProfile) -> BaseRunner:
        raise NotImplementedError

    @abstractmethod
    def supported_versions(self) -> Sequence[str]:
        raise NotImplementedError

    @abstractmethod
    def supported_backends(self) -> Sequence[str]:
        raise NotImplementedError

    @abstractmethod
    def supported_tasks(self) -> Sequence[str]:
        raise NotImplementedError

    def get_status_note(self) -> str:
        return ""

