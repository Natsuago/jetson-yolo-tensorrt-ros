# Jetson-YOLO-Tensorrt-ROS

[中文](README.md) | [English](README_en.md)

## 1. 项目概览

`jetson-yolo-tensorrt-ros` 是一个面向 NVIDIA Jetson 的 ROS Noetic YOLO 2D 目标检测项目。

当前上传到仓库的 ROS 包是 `yolo_ros`。它订阅 ROS 图像话题，运行 YOLO detect 推理，发布 `vision_msgs/Detection2DArray`，并可选发布 overlay 图像。

本项目不绑定任何相机。只要你的相机驱动发布 `sensor_msgs/Image`，就可以作为输入。

当前范围：

- 仅支持 ROS Noetic。
- 首版仅支持 detect。
- 支持 PT / ONNX / TensorRT engine。
- 支持 Ultralytics YOLOv8 / YOLO11 / YOLO12 / YOLO26。
- 支持 YOLOv5 classic，但需要外部 `ultralytics/yolov5` 仓库。
- 支持 YOLOv13 experimental provider。
- 不实现分割、姿态、分类、OBB、深度融合、点云、3D 检测、DeepStream 或手写 TensorRT decoder。

## 2. 快速开始

以下安装命令基于作者的 Jetson 设备环境。

| 项目 | 版本 |
| --- | --- |
| 设备 | NVIDIA Jetson Orin NX |
| JetPack | 5.1.4 |
| L4T / Jetson Linux | 35.6.0 |
| Ubuntu | 20.04 |
| CUDA | 11.4.19 |
| TensorRT | 8.5.2 |
| cuDNN | 8.6.0 |
| ROS | Noetic |
| Python | 3.8.10 |

安装 ROS 和系统依赖：

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

安装 Jetson PyTorch 和 torchvision wheel：

```bash
python3 -m pip install --no-cache-dir \
  https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl

python3 -m pip install --no-cache-dir \
  https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.16.2+c6f3977-cp38-cp38-linux_aarch64.whl
```

安装 Python 包：

```bash
python3 -m pip install pyyaml numpy
python3 -m pip install ultralytics==8.4.40 --no-deps
```

测试 Python 环境：

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

可选：冻结 torch 包：

```bash
python3 -m pip install --user --no-deps torchvision==0.16.2+c6f3977
python3 -m pip install --user --no-deps torch==2.1.0a0+41361538.nv23.06
```

克隆并编译：

```bash
cd ~
git clone git@github.com:Natsuago/jetson-yolo-tensorrt-ros.git
cd ~/jetson-yolo-tensorrt-ros

source /opt/ros/noetic/setup.bash
catkin_make -DCATKIN_ENABLE_TESTING=False -DCMAKE_BUILD_TYPE=Release
source devel/setup.bash
```

以 `yolo11n.pt` 为例，导出 FP16 TensorRT engine：

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

创建一个临时模型配置：

```bash
mkdir -p ~/temp
cp src/yolo_ros/config/model_profiles/yolo11_detect_engine_gpu_fp16.yaml ~/temp/yolo11_engine.yaml
```

编辑 `~/temp/yolo11_engine.yaml`，确认模型路径：

```yaml
model:
  path: ~/models/yolo11n.engine
  meta: ~/models/yolo11n.engine.meta.yaml
```

启动 ROS 节点：

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=~/temp/yolo11_engine.yaml
```

如果你的相机没有发布 `CameraInfo`，检测本身仍然可以运行；`yolo_ros` 的核心输入只依赖 `sensor_msgs/Image`。

## 3. 支持的 YOLO 模型

| 模型家族 | 任务 | 后端 | Provider | 说明 |
| --- | --- | --- | --- | --- |
| YOLOv5 classic | detect | pt, onnx, engine | `Yolov5ClassicProvider` | 需要外部 `ultralytics/yolov5` 仓库，DLA 不承诺稳定支持。 |
| YOLOv8 | detect | pt, onnx, engine | `UltralyticsProvider` | 使用 `ultralytics.YOLO(path).predict()`。 |
| YOLO11 | detect | pt, onnx, engine | `UltralyticsProvider` | 推荐默认测试目标。 |
| YOLO12 | detect | pt, onnx, engine | `UltralyticsProvider` | experimental / research-oriented。 |
| YOLOv13 | detect | pt, onnx, engine | `Yolov13Provider` | experimental third-party provider，DLA 不承诺稳定支持。 |
| YOLO26 | detect | pt, onnx, engine | `UltralyticsProvider` | end-to-end / NMS-free 行为需要额外确认。 |

## 4. 导出 YOLO11n 模型

ONNX 导出：

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

GPU TensorRT FP16 engine 导出：

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

DLA0 TensorRT FP16 engine 导出：

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

每次导出会在模型文件旁生成 metadata sidecar，例如：

```text
~/models/yolo11n.engine.meta.yaml
```

本项目的导出脚本会根据 accelerator 和 precision 规范化 engine 文件名：

```text
~/models/yolo11n_gpu_fp16.engine
~/models/yolo11n_gpu_fp16.engine.meta.yaml
~/models/yolo11n_dla0_fp16.engine
~/models/yolo11n_dla0_fp16.engine.meta.yaml
```

如果你从 GPU engine 切换到 DLA engine，必须同步切换 model profile。不要用 `engine.accelerator: gpu` 的 profile 去加载 DLA engine，否则节点会根据 metadata 拒绝启动。

## 5. 运行 ROS 节点

ONNX 示例：

```bash
cd ~/jetson-yolo-tensorrt-ros
source /opt/ros/noetic/setup.bash
source devel/setup.bash

roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_onnx.yaml
```

GPU TensorRT FP16 engine 示例：

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_engine_gpu_fp16.yaml
```

DLA0 TensorRT FP16 engine 示例：

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/image_raw \
  camera_info_topic:=/camera/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_engine_dla0_fp16.yaml
```

输出话题：

| 话题 | 类型 | 说明 |
| --- | --- | --- |
| `/yolo/detections` | `vision_msgs/Detection2DArray` | 2D 检测结果。 |
| `/yolo/overlay` | `sensor_msgs/Image` | 可选 overlay 图像，`publish_overlay=true` 时发布。 |

可视化 overlay 图像：

```bash
rosrun rqt_image_view rqt_image_view /yolo/overlay
```

如果系统没有 `rqt_image_view`：

```bash
sudo apt install -y ros-noetic-rqt-image-view
```

检查检测结果话题：

```bash
rostopic echo -n 1 /yolo/detections
rostopic hz /yolo/detections
```

## 6. 相机话题输入要求

| 输入 | 类型 | 是否必须 |
| --- | --- | --- |
| 图像话题 | `sensor_msgs/Image` | 必须 |
| 相机信息话题 | `sensor_msgs/CameraInfo` | 可选 |

输入图像需要能被 `cv_bridge` 转成 BGR8。任何 ROS 相机驱动都可以使用，只要它发布 `sensor_msgs/Image`。

## 7. Model Profiles 配置说明

配置目录：

```text
src/yolo_ros/config/model_profiles/
```

文件命名规则大致为：

```text
<model_family>_detect_<backend>.yaml
<model_family>_detect_engine_<accelerator>_<precision>.yaml
```

核心字段含义：

| 字段 | 含义 |
| --- | --- |
| `model.family` | 模型家族，例如 `ultralytics`、`yolov5_classic`、`yolov13`。 |
| `model.version` | YOLO 版本，例如 `"8"`、`"11"`、`"26"`。 |
| `model.task` | 当前只支持 `detect`。 |
| `model.backend` | 模型后端：`pt`、`onnx`、`engine`。 |
| `model.path` | 模型文件路径，指向 `.pt`、`.onnx` 或 `.engine`。 |
| `model.imgsz` | 推理输入尺寸，通常为 `640`。 |
| `model.class_names` | 类别名来源，默认 `coco`。 |
| `model.meta` | 导出 metadata sidecar 路径，通常是 `*.meta.yaml`。 |
| `inference.conf` | 置信度阈值。 |
| `inference.iou` | NMS IoU 阈值。 |
| `inference.classes` | 类别过滤，空列表表示不过滤。 |
| `inference.max_det` | 单帧最大检测框数量。 |
| `engine.accelerator` | TensorRT engine 加速目标：`gpu` 或 `dla`。 |
| `engine.dla_core` | DLA core，GPU engine 使用 `null`；Orin NX 8GB 通常只能用 `0`。 |
| `engine.precision` | `fp32`、`fp16` 或 `int8`。DLA 只支持 `fp16` / `int8`。 |
| `engine.allow_gpu_fallback` | DLA 不支持的层是否允许 fallback 到 GPU。 |
| `engine.nms` | 导出 engine 是否内置 NMS。 |
| `engine.end2end` | 是否为 end-to-end 导出。 |
| `external.yolov5_repo` | YOLOv5 classic 外部仓库路径。 |
| `ros.image_topic` | 默认订阅图像话题，可被 launch 参数覆盖。 |
| `ros.camera_info_topic` | 默认 CameraInfo 话题，可被 launch 参数覆盖。 |
| `ros.detections_topic` | 默认检测结果输出话题。 |
| `ros.overlay_topic` | 默认 overlay 输出话题。 |
| `ros.publish_overlay` | 是否发布 overlay。 |

当前配置文件列表：

| 文件 | 含义 |
| --- | --- |
| `yolo8_detect_pt.yaml` | YOLOv8 Ultralytics `.pt` detect profile。 |
| `yolo8_detect_onnx.yaml` | YOLOv8 Ultralytics ONNX detect profile。 |
| `yolo8_detect_engine.yaml` | YOLOv8 Ultralytics TensorRT engine detect profile，默认 GPU FP16。 |
| `yolo11_detect_pt.yaml` | YOLO11 Ultralytics `.pt` detect profile。 |
| `yolo11_detect_onnx.yaml` | YOLO11 Ultralytics ONNX detect profile。 |
| `yolo11_detect_engine.yaml` | YOLO11 Ultralytics TensorRT engine detect profile，兼容旧默认命名，默认 GPU FP16。 |
| `yolo11_detect_engine_gpu_fp16.yaml` | YOLO11 GPU TensorRT FP16 engine profile，推荐的 GPU engine 示例。 |
| `yolo11_detect_engine_dla0_fp16.yaml` | YOLO11 DLA0 TensorRT FP16 engine profile，experimental；作者环境已观察到 YOLO11n DLA0 FP16 可能 0 检出。 |
| `yolo12_detect_pt.yaml` | YOLO12 Ultralytics `.pt` detect profile，experimental。 |
| `yolo12_detect_onnx.yaml` | YOLO12 Ultralytics ONNX detect profile，experimental。 |
| `yolo12_detect_engine.yaml` | YOLO12 Ultralytics TensorRT engine detect profile，experimental，默认 GPU FP16。 |
| `yolo26_detect_pt.yaml` | YOLO26 Ultralytics `.pt` detect profile。 |
| `yolo26_detect_onnx.yaml` | YOLO26 Ultralytics ONNX detect profile。 |
| `yolo26_detect_engine.yaml` | YOLO26 Ultralytics TensorRT engine detect profile，默认 GPU FP16。 |
| `yolo26_detect_engine_gpu_fp16.yaml` | YOLO26 GPU TensorRT FP16 engine profile。 |
| `yolo26_detect_engine_dla0_fp16.yaml` | YOLO26 DLA0 TensorRT FP16 engine profile，experimental，允许 GPU fallback。 |
| `yolov5_classic_detect_pt.yaml` | YOLOv5 classic `.pt` detect profile，需要 `external.yolov5_repo`。 |
| `yolov5_classic_detect_onnx.yaml` | YOLOv5 classic ONNX detect profile，需要 `external.yolov5_repo`。 |
| `yolov5_classic_detect_engine.yaml` | YOLOv5 classic TensorRT engine detect profile，需要 `external.yolov5_repo`。 |
| `yolov13_detect_pt.yaml` | YOLOv13 `.pt` detect profile，experimental third-party provider。 |
| `yolov13_detect_onnx.yaml` | YOLOv13 ONNX detect profile，experimental third-party provider。 |
| `yolov13_detect_engine.yaml` | YOLOv13 TensorRT engine detect profile，experimental third-party provider。 |

## 8. TensorRT 和 DLA 注意事项

TensorRT engine 不是跨设备通用模型文件。建议在最终部署的 Jetson 上构建 `.engine`。

推荐流程：

- 先用 ONNX 跑通 ROS pipeline。
- 再使用 GPU TensorRT FP16 static engine 做第一版加速部署。
- 保留导出生成的 `.meta.yaml` 文件。

DLA 注意事项：

- DLA 只支持 FP16 和 INT8。
- DLA 只适用于 TensorRT engine，不适用于 ONNX。
- Orin NX 8GB 通常使用 `dla_core=0`。
- Orin NX 16GB 可能可以使用 `dla_core=0` 或 `dla_core=1`。
- DLA 的主要价值是降低功耗、释放 GPU、提升多流或多模型吞吐。
- DLA 不保证单帧 latency 一定低于 GPU TensorRT。
- 如果 `allow_gpu_fallback=true`，不支持 DLA 的层可能会运行在 GPU 上。
- 作者环境 JetPack 5.1.4 / TensorRT 8.5.2 / Ultralytics 8.4.40 下，`yolo11n` DLA0 FP16 engine 已观察到标准 `bus.jpg` 0 检出，而 PT 和 GPU FP16 engine 检出正常。
- 因此 YOLO11 DLA profile 标记为 experimental。部署前请先用静态图片验证 engine，若 DLA engine 0 检出，直接切回 GPU FP16 TensorRT engine。

Ultralytics DLA CLI 语法示例：

```bash
yolo export model=yolo11n.pt format=engine device="dla:0" half=True
```

Ultralytics DLA Python 语法示例：

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
model.export(format="engine", device="dla:0", half=True)
```

`trtexec` 只作为 fallback / diagnostic 工具保留。默认优先使用 YOLO 官方导出路径。

## 9. 已知限制

- 不支持 ROS 2。
- 当前只实现 2D detect。
- 不实现分割、姿态、OBB、分类、深度融合、点云、3D 检测。
- 不包含 DeepStream pipeline。
- 不包含手写 raw TensorRT decoder。
- YOLOv5 classic 需要外部 `ultralytics/yolov5` 仓库。
- YOLOv13 是 experimental，依赖第三方上游兼容性。
- DLA 支持主要面向 Ultralytics TensorRT engine；YOLOv5 classic 和 YOLOv13 的 DLA 不承诺稳定支持。
- YOLO11 DLA 在作者测试平台上不作为推荐部署路径；推荐使用 YOLO11 GPU TensorRT FP16 engine。

## 10. 参考链接

- JetPack 5.1.4: https://developer.nvidia.com/embedded/jetpack-sdk-514
- JetPack 5.1.4 Release Notes: https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-514/release-notes/index.html
- Ultralytics export: https://docs.ultralytics.com/modes/export/
- Ultralytics Jetson guide: https://docs.ultralytics.com/guides/nvidia-jetson/
- YOLOv5 classic export: https://docs.ultralytics.com/yolov5/tutorials/model_export/
- NVIDIA TensorRT trtexec: https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/quick-start-guide.html
- TensorRT version / hardware compatibility: https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/version-compatibility.html
- ROS Noetic vision_msgs Detection2DArray: https://docs.ros.org/en/noetic/api/vision_msgs/html/msg/Detection2DArray.html
- YOLOv13 third-party upstream: https://github.com/iMoonLab/yolov13
