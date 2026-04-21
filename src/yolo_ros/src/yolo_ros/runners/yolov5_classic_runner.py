from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from yolo_ros.core.detection_result import DetectionResult
from yolo_ros.core.exceptions import RunnerError
from yolo_ros.core.model_profile import ModelProfile
from yolo_ros.runners.base_runner import BaseRunner
from yolo_ros.utils.class_names import class_name_for, load_class_names, normalize_names


class Yolov5ClassicRunner(BaseRunner):
    def __init__(self, profile: ModelProfile):
        self.profile = profile
        self.model = None
        self.device = None
        self.stride = 32
        self.pt = True
        self.names = load_class_names(profile.model.class_names)
        self.letterbox = None
        self.non_max_suppression = None
        self.scale_boxes = None
        self.torch = None

    def _prepare_repo(self) -> Path:
        repo = Path(self.profile.external.yolov5_repo).expanduser()
        if not self.profile.external.yolov5_repo or not repo.exists():
            raise RunnerError(
                "YOLOv5 classic runtime requires external.yolov5_repo to point to a local "
                "clone of https://github.com/ultralytics/yolov5. Clone it and update the model profile."
            )
        if not (repo / "models" / "common.py").exists() or not (repo / "utils").exists():
            raise RunnerError(
                f"Invalid YOLOv5 repository path: {repo}. Expected ultralytics/yolov5 with models/common.py and utils/."
            )
        repo_str = str(repo)
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)
        return repo

    def load(self) -> None:
        repo = self._prepare_repo()
        model_path = Path(self.profile.model.path).expanduser()
        if model_path.is_absolute() and not model_path.exists():
            raise RunnerError(
                f"Model file not found: {model_path}. Update model.path in {self.profile.source_path or 'the profile'}."
            )

        try:
            import torch
            from models.common import DetectMultiBackend
            from utils.augmentations import letterbox
            from utils.general import check_img_size, non_max_suppression
            from utils.torch_utils import select_device

            try:
                from utils.general import scale_boxes
            except ImportError:
                from utils.general import scale_coords as scale_boxes
        except ImportError as exc:
            raise RunnerError(
                f"Failed to import YOLOv5 classic runtime from {repo}. "
                "Install YOLOv5 requirements and ensure external.yolov5_repo points to "
                "https://github.com/ultralytics/yolov5."
            ) from exc

        try:
            self.torch = torch
            self.letterbox = letterbox
            self.non_max_suppression = non_max_suppression
            self.scale_boxes = scale_boxes
            self.device = select_device("")
            try:
                self.model = DetectMultiBackend(str(model_path), device=self.device, dnn=False, data=None, fp16=False)
            except TypeError:
                self.model = DetectMultiBackend(str(model_path), device=self.device, dnn=False, data=None)
            stride_value = getattr(self.model, "stride", 32)
            if hasattr(stride_value, "max"):
                stride_value = stride_value.max()
            if hasattr(stride_value, "item"):
                stride_value = stride_value.item()
            if isinstance(stride_value, (list, tuple)):
                stride_value = max(stride_value)
            self.stride = int(stride_value)
            self.pt = bool(getattr(self.model, "pt", True))
            model_names = normalize_names(getattr(self.model, "names", None))
            if model_names:
                self.names = model_names
            check_img_size(self.profile.model.imgsz, s=self.stride)
        except Exception as exc:
            raise RunnerError(f"Failed to initialize YOLOv5 classic model {model_path}: {exc}") from exc

    def predict(
        self,
        cv_image: np.ndarray,
        conf: float,
        iou: float,
        imgsz,
        classes: Optional[Sequence[int]],
        max_det: int,
    ) -> List[DetectionResult]:
        if self.model is None:
            raise RunnerError("Yolov5ClassicRunner.load() must be called before predict().")

        try:
            img = self.letterbox(cv_image, imgsz, stride=self.stride, auto=self.pt)[0]
            img = img[..., ::-1].transpose((2, 0, 1))
            img = np.ascontiguousarray(img)

            tensor = self.torch.from_numpy(img).to(self.device)
            tensor = tensor.float() / 255.0
            if tensor.ndimension() == 3:
                tensor = tensor.unsqueeze(0)

            pred = self.model(tensor, augment=False, visualize=False)
            class_filter = None if not classes else [int(value) for value in classes]
            pred = self.non_max_suppression(
                pred,
                conf_thres=conf,
                iou_thres=iou,
                classes=class_filter,
                max_det=max_det,
            )
        except Exception as exc:
            raise RunnerError(f"YOLOv5 classic inference failed: {exc}") from exc

        detections: List[DetectionResult] = []
        if not pred:
            return detections

        det = pred[0]
        if det is None or len(det) == 0:
            return detections

        try:
            det[:, :4] = self.scale_boxes(tensor.shape[2:], det[:, :4], cv_image.shape).round()
            det_cpu = det.detach().cpu().numpy()
        except Exception as exc:
            raise RunnerError(f"YOLOv5 classic postprocess failed: {exc}") from exc

        for row in det_cpu:
            xmin, ymin, xmax, ymax, score, class_id = row[:6]
            cid = int(class_id)
            detections.append(
                DetectionResult(
                    class_id=cid,
                    class_name=class_name_for(cid, self.names),
                    score=float(score),
                    xmin=float(xmin),
                    ymin=float(ymin),
                    xmax=float(xmax),
                    ymax=float(ymax),
                )
            )
        return detections
