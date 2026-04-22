# Jetson-YOLO-Tensorrt-ROS

[中文](README.md) | [English](README_en.md)

## 1. Overview

`jetson-yolo-tensorrt-ros` is a ROS Noetic package for running YOLO 2D object detection on NVIDIA Jetson.

The uploaded ROS package is `yolo_ros`. It subscribes to a ROS image topic, runs YOLO detect inference, publishes `vision_msgs/Detection2DArray`, and can optionally publish an overlay image.

This project is camera-agnostic. Any camera can be used as long as it publishes a `sensor_msgs/Image` topic.

Current scope:

- ROS Noetic only.
- Detect task only.
- Supports PT / ONNX / TensorRT engine through official YOLO runtime paths.
- Supports Ultralytics YOLOv8 / YOLO11 / YOLO12 / YOLO26.
- Supports YOLOv5 classic through an external `ultralytics/yolov5` repository.
- Supports YOLOv13 as an experimental third-party provider.
- Does not implement segmentation, pose, classification, OBB, depth fusion, point cloud, 3D detection, DeepStream, or a handwritten raw TensorRT decoder.

## 2. Quick Start

The following installation commands are based on the author's Jetson environment.

| Item | Version |
| --- | --- |
| Device | NVIDIA Jetson Orin NX |
| JetPack | 5.1.4 |
| L4T / Jetson Linux | 35.6.0 |
| Ubuntu | 20.04 |
| CUDA | 11.4.19 |
| TensorRT | 8.5.2 |
| cuDNN | 8.6.0 |
| ROS | Noetic |
| Python | 3.8.10 |

Install ROS and system dependencies:

```bash
sudo apt update
sudo apt install -y \
  ros-noetic-vision-msgs \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-tf \
  ros-noetic-tf2-ros \
  ros-noetic-diagnostic-updater \
  libopenblas-dev \
  libopenblas-base
```

Install Jetson PyTorch and torchvision wheels:

```bash
python3 -m pip install --no-cache-dir \
  https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl

python3 -m pip install --no-cache-dir \
  https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.16.2+c6f3977-cp38-cp38-linux_aarch64.whl
```

Install Python packages:

```bash
python3 -m pip install pyyaml numpy
python3 -m pip install ultralytics==8.4.40 --no-deps
```

Test the Python environment:

```bash
python3 - <<'PY'
import torch, torchvision
print("torch:", torch.__version__)
print("cuda:", torch.cuda.is_available())
print("torchvision:", torchvision.__version__)

from ultralytics import YOLO
print("ultralytics import ok")
PY
```

Optionally freeze the torch packages in the user site:

```bash
python3 -m pip install --user --no-deps torchvision==0.16.2+c6f3977
python3 -m pip install --user --no-deps torch==2.1.0a0+41361538.nv23.06
```

Clone and build:

```bash
cd ~
git clone git@github.com:Natsuago/jetson-yolo-tensorrt-ros.git
cd ~/jetson-yolo-tensorrt-ros

source /opt/ros/noetic/setup.bash
catkin_make -DCATKIN_ENABLE_TESTING=False -DCMAKE_BUILD_TYPE=Release
source devel/setup.bash
```

Export a YOLO11n FP16 TensorRT engine:

```bash
mkdir -p ~/models

python3 tools/export/export_ultralytics.py \
  --model yolo11n.pt \
  --format engine \
  --out-dir ~/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0 \
  --accelerator gpu \
  --dla-core 0 \
  --allow-gpu-fallback false \
  --data "" \
  --fraction 1.0
```

Create a temporary model profile:

```bash
mkdir -p ~/temp
cp src/yolo_ros/config/model_profiles/yolo11_detect_engine_gpu_fp16.yaml ~/temp/yolo11_engine.yaml
```

Edit `~/temp/yolo11_engine.yaml` and set:

```yaml
model:
  path: ~/models/yolo11n.engine
  meta: ~/models/yolo11n.engine.meta.yaml
```

Run the ROS node with your camera image topic:

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=~/temp/yolo11_engine.yaml
```

If your camera does not publish `CameraInfo`, the detector can still run. The core input requirement is `sensor_msgs/Image`.

## 3. Supported YOLO Models

| Model family | Task | Backends | Provider | Notes |
| --- | --- | --- | --- | --- |
| YOLOv5 classic | detect | pt, onnx, engine | `Yolov5ClassicProvider` | Requires an external `ultralytics/yolov5` repo through `external.yolov5_repo`. DLA is not promised as stable. |
| YOLOv8 | detect | pt, onnx, engine | `UltralyticsProvider` | Uses `ultralytics.YOLO(path).predict()`. |
| YOLO11 | detect | pt, onnx, engine | `UltralyticsProvider` | Recommended default test target. |
| YOLO12 | detect | pt, onnx, engine | `UltralyticsProvider` | Experimental / research-oriented. |
| YOLOv13 | detect | pt, onnx, engine | `Yolov13Provider` | Experimental third-party provider. DLA is not promised as stable. |
| YOLO26 | detect | pt, onnx, engine | `UltralyticsProvider` | End-to-end / NMS-free behavior requires care. |

## 4. Export YOLO11n Models

ONNX export:

```bash
cd ~/jetson-yolo-tensorrt-ros
mkdir -p ~/models

python3 tools/export/export_ultralytics.py \
  --model yolo11n.pt \
  --format onnx \
  --out-dir ~/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp32 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0 \
  --accelerator gpu \
  --dla-core 0 \
  --allow-gpu-fallback false \
  --data "" \
  --fraction 1.0
```

GPU TensorRT FP16 engine export:

```bash
cd ~/jetson-yolo-tensorrt-ros
mkdir -p ~/models

python3 tools/export/export_ultralytics.py \
  --model yolo11n.pt \
  --format engine \
  --out-dir ~/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0 \
  --accelerator gpu \
  --dla-core 0 \
  --allow-gpu-fallback false \
  --data "" \
  --fraction 1.0
```

DLA0 TensorRT FP16 engine export:

```bash
cd ~/jetson-yolo-tensorrt-ros
mkdir -p ~/models

python3 tools/export/export_ultralytics.py \
  --model yolo11n.pt \
  --format engine \
  --out-dir ~/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0 \
  --accelerator dla \
  --dla-core 0 \
  --allow-gpu-fallback true \
  --data "" \
  --fraction 1.0
```

Each export writes a metadata sidecar next to the model artifact, for example:

```text
~/models/yolo11n.engine.meta.yaml
```

## 5. Run The ROS Node

ONNX example:

```bash
cd ~/jetson-yolo-tensorrt-ros
source /opt/ros/noetic/setup.bash
source devel/setup.bash

roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_onnx.yaml
```

GPU TensorRT FP16 engine example:

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_engine_gpu_fp16.yaml
```

Published topics:

| Topic | Type | Description |
| --- | --- | --- |
| `/yolo/detections` | `vision_msgs/Detection2DArray` | 2D detection results. |
| `/yolo/overlay` | `sensor_msgs/Image` | Optional overlay image when `publish_overlay=true`. |

## 6. Camera Topic Requirements

| Input | Type | Required |
| --- | --- | --- |
| image topic | `sensor_msgs/Image` | Yes |
| camera info topic | `sensor_msgs/CameraInfo` | Optional |

The input image must be convertible by `cv_bridge` to BGR8. Any ROS camera driver can be used if it publishes `sensor_msgs/Image`.

## 7. Model Profile Files

Profile directory:

```text
src/yolo_ros/config/model_profiles/
```

File naming convention:

```text
<model_family>_detect_<backend>.yaml
<model_family>_detect_engine_<accelerator>_<precision>.yaml
```

Core fields:

| Field | Meaning |
| --- | --- |
| `model.family` | Model family, such as `ultralytics`, `yolov5_classic`, or `yolov13`. |
| `model.version` | YOLO version, such as `"8"`, `"11"`, or `"26"`. |
| `model.task` | Only `detect` is currently supported. |
| `model.backend` | Runtime backend: `pt`, `onnx`, or `engine`. |
| `model.path` | Path to the `.pt`, `.onnx`, or `.engine` model file. |
| `model.imgsz` | Inference image size, usually `640`. |
| `model.class_names` | Class name source, default `coco`. |
| `model.meta` | Export metadata sidecar path, usually `*.meta.yaml`. |
| `inference.conf` | Confidence threshold. |
| `inference.iou` | NMS IoU threshold. |
| `inference.classes` | Optional class filter. Empty list means all classes. |
| `inference.max_det` | Maximum detections per frame. |
| `engine.accelerator` | TensorRT accelerator target: `gpu` or `dla`. |
| `engine.dla_core` | DLA core. GPU engine uses `null`; Orin NX 8GB usually uses `0`. |
| `engine.precision` | `fp32`, `fp16`, or `int8`. DLA supports only `fp16` / `int8`. |
| `engine.allow_gpu_fallback` | Whether unsupported DLA layers may fall back to GPU. |
| `engine.nms` | Whether the exported engine includes NMS. |
| `engine.end2end` | Whether the model is exported as end-to-end. |
| `external.yolov5_repo` | External YOLOv5 classic repository path. |
| `ros.image_topic` | Default image topic, overridable by launch args. |
| `ros.camera_info_topic` | Default CameraInfo topic, overridable by launch args. |
| `ros.detections_topic` | Default detection output topic. |
| `ros.overlay_topic` | Default overlay output topic. |
| `ros.publish_overlay` | Whether to publish overlay images. |

Current profile files:

| File | Meaning |
| --- | --- |
| `yolo8_detect_pt.yaml` | YOLOv8 Ultralytics `.pt` detect profile. |
| `yolo8_detect_onnx.yaml` | YOLOv8 Ultralytics ONNX detect profile. |
| `yolo8_detect_engine.yaml` | YOLOv8 Ultralytics TensorRT engine detect profile, default GPU FP16. |
| `yolo11_detect_pt.yaml` | YOLO11 Ultralytics `.pt` detect profile. |
| `yolo11_detect_onnx.yaml` | YOLO11 Ultralytics ONNX detect profile. |
| `yolo11_detect_engine.yaml` | YOLO11 Ultralytics TensorRT engine detect profile, legacy default name, default GPU FP16. |
| `yolo11_detect_engine_gpu_fp16.yaml` | YOLO11 GPU TensorRT FP16 engine profile, recommended GPU engine example. |
| `yolo11_detect_engine_dla0_fp16.yaml` | YOLO11 DLA0 TensorRT FP16 engine profile with GPU fallback enabled. |
| `yolo12_detect_pt.yaml` | YOLO12 Ultralytics `.pt` detect profile, experimental. |
| `yolo12_detect_onnx.yaml` | YOLO12 Ultralytics ONNX detect profile, experimental. |
| `yolo12_detect_engine.yaml` | YOLO12 Ultralytics TensorRT engine detect profile, experimental, default GPU FP16. |
| `yolo26_detect_pt.yaml` | YOLO26 Ultralytics `.pt` detect profile. |
| `yolo26_detect_onnx.yaml` | YOLO26 Ultralytics ONNX detect profile. |
| `yolo26_detect_engine.yaml` | YOLO26 Ultralytics TensorRT engine detect profile, default GPU FP16. |
| `yolo26_detect_engine_gpu_fp16.yaml` | YOLO26 GPU TensorRT FP16 engine profile. |
| `yolo26_detect_engine_dla0_fp16.yaml` | YOLO26 DLA0 TensorRT FP16 engine profile with GPU fallback enabled. |
| `yolov5_classic_detect_pt.yaml` | YOLOv5 classic `.pt` detect profile, requires `external.yolov5_repo`. |
| `yolov5_classic_detect_onnx.yaml` | YOLOv5 classic ONNX detect profile, requires `external.yolov5_repo`. |
| `yolov5_classic_detect_engine.yaml` | YOLOv5 classic TensorRT engine detect profile, requires `external.yolov5_repo`. |
| `yolov13_detect_pt.yaml` | YOLOv13 `.pt` detect profile, experimental third-party provider. |
| `yolov13_detect_onnx.yaml` | YOLOv13 ONNX detect profile, experimental third-party provider. |
| `yolov13_detect_engine.yaml` | YOLOv13 TensorRT engine detect profile, experimental third-party provider. |

## 8. TensorRT And DLA Notes

TensorRT engine files are not portable model files. Build `.engine` files on the final deployment Jetson.

Recommended flow:

- Start with ONNX to verify the ROS pipeline.
- Use GPU TensorRT FP16 static engine for the first accelerated deployment.
- Keep the `.meta.yaml` sidecar next to the exported model.

DLA notes:

- DLA supports FP16 and INT8 only.
- DLA is available only for TensorRT engine export/runtime, not ONNX.
- On Orin NX 8GB, use `dla_core=0`.
- On Orin NX 16GB, `dla_core=0` or `dla_core=1` may be available.
- DLA mainly helps reduce power, free GPU resources, and improve multi-stream or multi-model throughput.
- DLA does not guarantee lower single-frame latency than GPU TensorRT.
- If `allow_gpu_fallback=true`, unsupported DLA layers may run on GPU.

Ultralytics DLA CLI example:

```bash
yolo export model=yolo11n.pt format=engine device="dla:0" half=True
```

Ultralytics DLA Python example:

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
model.export(format="engine", device="dla:0", half=True)
```

`trtexec` is kept only as a fallback / diagnostic tool. Prefer official YOLO export first.

## 9. Known Limitations

- ROS 2 is not supported.
- Only 2D detect is implemented.
- Segmentation, pose, OBB, classification, depth fusion, point clouds, and 3D detection are not implemented.
- DeepStream is not part of this project.
- No handwritten raw TensorRT decoder is included.
- YOLOv5 classic requires an external `ultralytics/yolov5` repository.
- YOLOv13 is experimental and depends on third-party upstream compatibility.
- DLA support is focused on Ultralytics TensorRT engine export/runtime; YOLOv5 classic and YOLOv13 DLA are not promised as stable.

## 10. References

- JetPack 5.1.4: https://developer.nvidia.com/embedded/jetpack-sdk-514
- JetPack 5.1.4 Release Notes: https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-514/release-notes/index.html
- Ultralytics export: https://docs.ultralytics.com/modes/export/
- Ultralytics Jetson guide: https://docs.ultralytics.com/guides/nvidia-jetson/
- YOLOv5 classic export: https://docs.ultralytics.com/yolov5/tutorials/model_export/
- NVIDIA TensorRT trtexec: https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/quick-start-guide.html
- TensorRT version / hardware compatibility: https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/version-compatibility.html
- ROS Noetic vision_msgs Detection2DArray: https://docs.ros.org/en/noetic/api/vision_msgs/html/msg/Detection2DArray.html
- YOLOv13 third-party upstream: https://github.com/iMoonLab/yolov13

