from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping, Union

from yolo_ros.utils.yaml_utils import load_yaml_file


COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis",
    "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass",
    "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed",
    "dining table", "toilet", "tv", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush",
]


def coco_mapping() -> Dict[int, str]:
    return {idx: name for idx, name in enumerate(COCO_NAMES)}


def normalize_names(names: Union[Mapping, list, tuple, None]) -> Dict[int, str]:
    if names is None:
        return {}
    if isinstance(names, Mapping):
        return {int(key): str(value) for key, value in names.items()}
    return {idx: str(value) for idx, value in enumerate(names)}


def load_class_names(source: str) -> Dict[int, str]:
    if not source:
        return {}
    normalized = source.strip().lower()
    if normalized == "coco":
        return coco_mapping()

    path = Path(source).expanduser()
    if path.exists():
        data = load_yaml_file(str(path))
        if "names" in data:
            return normalize_names(data["names"])
        return normalize_names(data)

    if "," in source:
        return {idx: name.strip() for idx, name in enumerate(source.split(","))}

    return {}


def class_name_for(class_id: int, names: Mapping[int, str]) -> str:
    return names.get(int(class_id), f"class_{int(class_id)}")

