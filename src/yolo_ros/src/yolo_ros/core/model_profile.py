from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from yolo_ros.core.exceptions import ProfileError
from yolo_ros.utils.yaml_utils import load_yaml_file


@dataclass
class ModelConfig:
    family: str
    version: str
    task: str
    backend: str
    path: str
    imgsz: Any
    class_names: str = "coco"
    meta: str = ""
    status: str = "stable"
    note: str = ""
    nms: Optional[bool] = None
    end2end: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceConfig:
    conf: float = 0.25
    iou: float = 0.45
    classes: List[int] = field(default_factory=list)
    max_det: int = 300


@dataclass
class ExternalConfig:
    yolov5_repo: str = ""


@dataclass
class RosConfig:
    image_topic: str = "/camera/color/image_raw"
    camera_info_topic: str = "/camera/color/camera_info"
    detections_topic: str = "/yolo/detections"
    overlay_topic: str = "/yolo/overlay"
    publish_overlay: bool = True
    queue_size: int = 1


@dataclass
class ModelProfile:
    model: ModelConfig
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    external: ExternalConfig = field(default_factory=ExternalConfig)
    ros: RosConfig = field(default_factory=RosConfig)
    source_path: str = ""

    @classmethod
    def from_file(cls, path: str) -> "ModelProfile":
        data = load_yaml_file(path)
        profile = cls.from_dict(data)
        profile.source_path = str(Path(path).expanduser())
        return profile

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelProfile":
        if "model" not in data:
            raise ProfileError("Model profile must contain a 'model' section.")

        model_data = dict(data.get("model") or {})
        required = ["family", "version", "task", "backend", "path", "imgsz"]
        missing = [key for key in required if key not in model_data]
        if missing:
            raise ProfileError(f"Model profile missing model fields: {', '.join(missing)}")

        known_model_keys = {
            "family", "version", "task", "backend", "path", "imgsz",
            "class_names", "meta", "status", "note", "nms", "end2end",
        }
        extra = {key: value for key, value in model_data.items() if key not in known_model_keys}
        model = ModelConfig(
            family=str(model_data["family"]),
            version=str(model_data["version"]),
            task=str(model_data["task"]),
            backend=str(model_data["backend"]),
            path=str(model_data["path"]),
            imgsz=model_data["imgsz"],
            class_names=str(model_data.get("class_names", "coco") or ""),
            meta=str(model_data.get("meta", "") or ""),
            status=str(model_data.get("status", "stable") or "stable"),
            note=str(model_data.get("note", "") or ""),
            nms=model_data.get("nms"),
            end2end=model_data.get("end2end"),
            extra=extra,
        )

        inference_data = data.get("inference") or {}
        inference = InferenceConfig(
            conf=float(inference_data.get("conf", 0.25)),
            iou=float(inference_data.get("iou", 0.45)),
            classes=[int(value) for value in (inference_data.get("classes") or [])],
            max_det=int(inference_data.get("max_det", 300)),
        )

        external_data = data.get("external") or {}
        external = ExternalConfig(
            yolov5_repo=str(external_data.get("yolov5_repo", "") or ""),
        )

        ros_data = data.get("ros") or {}
        ros = RosConfig(
            image_topic=str(ros_data.get("image_topic", "/camera/color/image_raw")),
            camera_info_topic=str(ros_data.get("camera_info_topic", "/camera/color/camera_info")),
            detections_topic=str(ros_data.get("detections_topic", "/yolo/detections")),
            overlay_topic=str(ros_data.get("overlay_topic", "/yolo/overlay")),
            publish_overlay=bool(ros_data.get("publish_overlay", True)),
            queue_size=int(ros_data.get("queue_size", 1)),
        )

        profile = cls(model=model, inference=inference, external=external, ros=ros)
        profile.validate_basic()
        return profile

    def validate_basic(self) -> None:
        if self.model.task != "detect":
            raise ProfileError(
                f"Only task=detect is implemented in this release, got task={self.model.task!r}."
            )
        if self.model.backend not in {"pt", "onnx", "engine"}:
            raise ProfileError(
                f"Unsupported backend={self.model.backend!r}; expected pt, onnx, or engine."
            )
        if self.inference.max_det <= 0:
            raise ProfileError("inference.max_det must be positive.")
        if not (0.0 <= self.inference.conf <= 1.0):
            raise ProfileError("inference.conf must be between 0.0 and 1.0.")
        if not (0.0 <= self.inference.iou <= 1.0):
            raise ProfileError("inference.iou must be between 0.0 and 1.0.")


def _artifact_section(meta: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("engine", "export", "artifact"):
        section = meta.get(key)
        if isinstance(section, dict):
            return section
    return {}


def _same_imgsz(left: Any, right: Any) -> bool:
    def normalize(value: Any) -> Any:
        if isinstance(value, (list, tuple)) and len(value) == 1:
            return int(value[0])
        if isinstance(value, (list, tuple)):
            return [int(item) for item in value]
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    return normalize(left) == normalize(right)


def check_metadata_compatibility(
    profile: ModelProfile,
    warn: Callable[[str], None],
) -> None:
    meta_path = profile.model.meta
    if not meta_path:
        if profile.model.backend in {"onnx", "engine"}:
            warn(
                "No model.meta sidecar configured. Runtime will continue, but export "
                "settings cannot be checked."
            )
        return

    path = Path(meta_path).expanduser()
    if not path.exists():
        warn(f"Metadata sidecar not found: {path}. Runtime will continue without export checks.")
        return

    meta = load_yaml_file(str(path))
    model_meta = meta.get("model") or {}
    artifact = _artifact_section(meta)

    family = model_meta.get("family")
    if family and str(family) != profile.model.family:
        raise ProfileError(
            f"Metadata family={family!r} does not match profile family={profile.model.family!r}."
        )

    task = model_meta.get("task")
    if task and str(task) != "detect":
        raise ProfileError(f"Metadata task={task!r} is not supported; only detect is implemented.")

    fmt = artifact.get("format")
    if fmt and str(fmt) != profile.model.backend:
        raise ProfileError(
            f"Metadata format={fmt!r} does not match profile backend={profile.model.backend!r}."
        )

    meta_imgsz = artifact.get("imgsz")
    dynamic = artifact.get("dynamic")
    if dynamic is False and meta_imgsz is not None and not _same_imgsz(meta_imgsz, profile.model.imgsz):
        raise ProfileError(
            f"Static export imgsz={meta_imgsz!r} does not match profile imgsz={profile.model.imgsz!r}."
        )

    for key in ("nms", "end2end"):
        expected = getattr(profile.model, key, None)
        actual = artifact.get(key)
        if expected is not None and actual is not None and bool(expected) != bool(actual):
            warn(
                f"Metadata {key}={actual!r} does not match profile model.{key}={expected!r}. "
                "Verify preprocessing and postprocessing compatibility."
            )

