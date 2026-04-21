class YoloRosError(Exception):
    """Base exception for yolo_ros."""


class ProfileError(YoloRosError):
    """Raised when a model profile is invalid or inconsistent."""


class ProviderError(YoloRosError):
    """Raised when a provider cannot support a profile."""


class RunnerError(YoloRosError):
    """Raised when a runtime backend cannot load or run a model."""

