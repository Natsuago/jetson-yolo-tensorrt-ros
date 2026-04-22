from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from yolo_ros.core.exceptions import ProfileError
from yolo_ros.utils.yaml_utils import load_yaml_file, parse_bool


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
class EngineConfig:
    accelerator: str = "gpu"
    dla_core: Optional[int] = None
    precision: str = "fp16"
    allow_gpu_fallback: bool = False
    nms: Optional[bool] = False
    end2end: Optional[bool] = None


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
    engine: Optional[EngineConfig] = None
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

        engine = None
        engine_data = data.get("engine")
        if engine_data is not None or model.backend == "engine":
            engine_data = engine_data or {}
            dla_core = engine_data.get("dla_core")
            engine = EngineConfig(
                accelerator=str(engine_data.get("accelerator", "gpu") or "gpu"),
                dla_core=None if dla_core is None else int(dla_core),
                precision=str(engine_data.get("precision", "fp16") or "fp16"),
                allow_gpu_fallback=parse_bool(engine_data.get("allow_gpu_fallback", False)),
                nms=engine_data.get("nms", model.nms),
                end2end=engine_data.get("end2end", model.end2end),
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

        profile = cls(model=model, inference=inference, engine=engine, external=external, ros=ros)
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
        if self.engine is not None:
            if self.model.backend != "engine":
                raise ProfileError("The engine section is only valid when model.backend=engine.")
            if self.engine.accelerator not in {"gpu", "dla"}:
                raise ProfileError("engine.accelerator must be 'gpu' or 'dla'.")
            if self.engine.precision not in {"fp32", "fp16", "int8"}:
                raise ProfileError("engine.precision must be fp32, fp16, or int8.")
            if self.engine.accelerator == "gpu" and self.engine.dla_core is not None:
                raise ProfileError("engine.dla_core must be null when engine.accelerator=gpu.")
            if self.engine.accelerator == "dla":
                if self.engine.dla_core not in {0, 1}:
                    raise ProfileError("engine.dla_core must be 0 or 1 when engine.accelerator=dla.")
                if self.engine.precision not in {"fp16", "int8"}:
                    raise ProfileError("DLA engine precision must be fp16 or int8.")
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
    info: Optional[Callable[[str], None]] = None,
) -> None:
    info = info or (lambda _message: None)
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

    if profile.engine is not None:
        comparisons = {
            "accelerator": profile.engine.accelerator,
            "dla_core": profile.engine.dla_core,
            "precision": profile.engine.precision,
        }
        for key, expected in comparisons.items():
            actual = artifact.get(key)
            if actual is not None and expected is not None and str(actual) != str(expected):
                raise ProfileError(
                    f"Metadata {key}={actual!r} does not match profile engine.{key}={expected!r}."
                )

        accelerator = str(artifact.get("accelerator", profile.engine.accelerator))
        dla_core = artifact.get("dla_core", profile.engine.dla_core)
        allow_gpu_fallback = artifact.get("allow_gpu_fallback", profile.engine.allow_gpu_fallback)
        if accelerator == "dla":
            info(f"TensorRT DLA engine selected: dla_core={dla_core}.")
            if parse_bool(allow_gpu_fallback):
                warn(
                    "TensorRT DLA engine allows GPU fallback. Some layers may run on GPU; "
                    "DLA does not guarantee lower latency than GPU TensorRT."
                )
            if profile.model.family == "ultralytics" and profile.model.version == "11":
                warn(
                    "Known compatibility risk: Ultralytics YOLO11 TensorRT DLA engines have "
                    "been observed to return zero detections on JetPack 5.1.4 / TensorRT 8.5.2 "
                    "/ Ultralytics 8.4.40. Validate the engine with a static image before ROS "
                    "deployment; prefer GPU FP16 TensorRT if detections are empty."
                )
            if (
                artifact.get("allow_gpu_fallback") is not None
                and parse_bool(artifact.get("allow_gpu_fallback")) != profile.engine.allow_gpu_fallback
            ):
                warn(
                    "Metadata allow_gpu_fallback does not match profile engine.allow_gpu_fallback. "
                    "Verify the engine was built with the intended fallback policy."
                )

    for key in ("nms", "end2end"):
        expected = getattr(profile.engine, key, None) if profile.engine is not None else getattr(profile.model, key, None)
        actual = artifact.get(key)
        if expected is not None and actual is not None and bool(expected) != bool(actual):
            warn(
                f"Metadata {key}={actual!r} does not match profile {key}={expected!r}. "
                "Verify preprocessing and postprocessing compatibility."
            )
