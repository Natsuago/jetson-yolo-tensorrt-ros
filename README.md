# jetson-yolo-tensorrt-ros

## 1. Overview

`jetson-yolo-tensorrt-ros` is a ROS Noetic only catkin workspace for running 2D YOLO detect inference on NVIDIA Jetson from any ROS `sensor_msgs/Image` topic.

The workspace contains two packages:

- `yolo_ros`: camera-agnostic YOLO detect node. It subscribes to `sensor_msgs/Image`, runs YOLO inference, publishes `vision_msgs/Detection2DArray`, and can publish an overlay `sensor_msgs/Image`.
- `realsense_camera`: RealSense D455 launch and diagnostic wrapper. It does not implement or vendor the Intel RealSense driver. It includes the official `realsense2_camera` `rs_camera.launch` at runtime.

This first release implements detect only. Segmentation, pose, classification, OBB, depth fusion, point clouds, and 3D detection are intentionally not implemented.

Official references kept for deployment work:

- JetPack 5.1.4: https://developer.nvidia.com/embedded/jetpack-sdk-514
- JetPack 5.1.4 Release Notes: https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-514/release-notes/index.html
- Ultralytics export: https://docs.ultralytics.com/modes/export/
- Ultralytics Jetson guide: https://docs.ultralytics.com/guides/nvidia-jetson/
- YOLOv5 classic export: https://docs.ultralytics.com/yolov5/tutorials/model_export/
- NVIDIA TensorRT trtexec: https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/quick-start-guide.html
- TensorRT version / hardware compatibility: https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/version-compatibility.html
- ROS Noetic vision_msgs Detection2DArray: https://docs.ros.org/en/noetic/api/vision_msgs/html/msg/Detection2DArray.html
- RealSense ROS1 legacy wrapper: https://github.com/IntelRealSense/realsense-ros/tree/ros1-legacy
- YOLOv13 third-party upstream: https://github.com/iMoonLab/yolov13

## 2. Tested Platform

Reference platform:

- NVIDIA Jetson Orin NX
- JetPack 5.1.4
- L4T / Jetson Linux 35.6.0
- Ubuntu 20.04
- CUDA 11.4.19
- TensorRT 8.5.2
- cuDNN 8.6.0
- ROS Noetic
- Python 3
- Intel RealSense D455

Jetson PyTorch installation is platform-specific. Follow NVIDIA and Ultralytics Jetson instructions for the correct wheel and dependency set. This README intentionally does not pin a PyTorch wheel URL.

## 3. Repository Layout

```text
jetson-yolo-tensorrt-ros/
  README.md
  LICENSE
  .gitignore
  src/
    CMakeLists.txt
    yolo_ros/
    realsense_camera/
  tools/
    export/
    realsense/
    diagnostics/
  weights/
    .gitkeep
```

`weights/` is intentionally empty except for `.gitkeep`. Do not commit `.pt`, `.onnx`, `.engine`, `.plan`, `.trt`, `.weights`, videos, bags, or image dumps.

## 4. Packages

### yolo_ros

`yolo_ros` is independent of RealSense. It only requires an input `sensor_msgs/Image` topic.

Main behavior:

- Subscribes to image topic, for example `/camera/color/image_raw`.
- Optionally subscribes to `CameraInfo`, for example `/camera/color/camera_info`. CameraInfo is optional but recommended for downstream consumers.
- Runs detect inference through a provider and runner abstraction.
- Publishes `vision_msgs/Detection2DArray`.
- Optionally publishes an overlay image.

The code is structured for later `seg`, `pose`, `cls`, and `obb` extension, but those tasks are not implemented in this release.

### realsense_camera

`realsense_camera` is a launch/config/check wrapper for D455. It does not rewrite librealsense or realsense-ros.

Runtime behavior:

- Includes `$(find realsense2_camera)/launch/rs_camera.launch`.
- Starts color stream only by default.
- Does not enable depth fusion, point clouds, aligned depth, infra, gyro, or accel by default.
- Provides a convenience `d455_yolo.launch` that starts D455 color plus `yolo_ros`.

If `realsense2_camera` is missing, the package itself can still be built, but `d455_color.launch` cannot run until the official wrapper is installed or built.

## 5. Supported YOLO Models

| Model family | Task | Backends | Provider | Notes |
| --- | --- | --- | --- | --- |
| YOLOv5 classic | detect | pt, onnx, engine | `Yolov5ClassicProvider` | Requires external `ultralytics/yolov5` repo via `external.yolov5_repo`. |
| YOLOv8 | detect | pt, onnx, engine | `UltralyticsProvider` | Uses `ultralytics.YOLO(path).predict()`. |
| YOLO11 | detect | pt, onnx, engine | `UltralyticsProvider` | Uses `ultralytics.YOLO(path).predict()`. |
| YOLO12 | detect | pt, onnx, engine | `UltralyticsProvider` | Experimental / research-oriented. Verify upstream runtime compatibility. |
| YOLOv13 | detect | pt, onnx, engine | `Yolov13Provider` | Experimental third-party provider. Prefer iMoonLab/yolov13 ultralytics-style runtime. |
| YOLO26 | detect | pt, onnx, engine | `UltralyticsProvider` | End-to-end / NMS-free behavior requires care. Verify output schema and postprocess assumptions. |

No raw TensorRT decoder is implemented in this release. Engine inference is routed through the official runtime paths:

- Ultralytics-family models: `ultralytics.YOLO(path).predict()`.
- YOLOv5 classic: external `ultralytics/yolov5` `DetectMultiBackend` and official postprocess utilities.

## 6. Installation

Install ROS dependencies:

```bash
sudo apt update
sudo apt install -y \
  ros-noetic-vision-msgs \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  ros-noetic-tf \
  ros-noetic-tf2-ros \
  ros-noetic-diagnostic-updater
```

Install Python dependencies:

```bash
pip3 install pyyaml numpy ultralytics
```

Build the workspace:

```bash
cd /home/bdi/jetson-yolo-tensorrt-ros
source /opt/ros/noetic/setup.bash
catkin_make -DCATKIN_ENABLE_TESTING=False -DCMAKE_BUILD_TYPE=Release
source devel/setup.bash
```

Check whether the RealSense ROS wrapper already exists:

```bash
rospack find realsense2_camera
```

If it is missing, choose one official wrapper path:

```bash
sudo apt install ros-noetic-realsense2-camera ros-noetic-realsense2-description
```

or build the official ROS1 legacy wrapper from source:

```bash
bash tools/realsense/setup_realsense_ros1_legacy.sh --clone --build
```

The setup helper does not vendor `realsense-ros` into this repository history. It can clone the official repo into `src/realsense-ros` in your local workspace when requested.

## 7. RealSense D455 Setup

The default librealsense source root is:

```text
/home/bdi/thridprty/librealsense
```

The check scripts verify this source tree, installed or built tools, pkg-config/CMake visibility, and the ROS wrapper:

```bash
python3 src/realsense_camera/scripts/check_realsense_env.py \
  --librealsense-root /home/bdi/thridprty/librealsense
```

Shell-only librealsense root check:

```bash
bash tools/realsense/check_librealsense_root.sh \
  --librealsense-root /home/bdi/thridprty/librealsense
```

If `realsense2_camera` is not found, the diagnostic output will say:

```text
realsense2_camera is not found. Install ros-noetic-realsense2-camera or build IntelRealSense/realsense-ros ros1-legacy from source.
```

The helper script supports:

```bash
bash tools/realsense/setup_realsense_ros1_legacy.sh --help
```

Common source-build command:

```bash
bash tools/realsense/setup_realsense_ros1_legacy.sh --clone --build
```

If your librealsense was built from source but not installed, make sure `realsense2` is discoverable by CMake or pkg-config. If needed, install it or set `CMAKE_PREFIX_PATH` and `LD_LIBRARY_PATH` to your librealsense build/install location.

Launch D455 color only:

```bash
roslaunch realsense_camera d455_color.launch
```

Default color topics:

```text
/camera/color/image_raw
/camera/color/camera_info
```

Check topics:

```bash
rostopic list | grep /camera/color
rostopic hz /camera/color/image_raw
```

Wait for topics:

```bash
python3 src/realsense_camera/scripts/wait_for_d455.py \
  --image-topic /camera/color/image_raw \
  --camera-info-topic /camera/color/camera_info \
  --timeout 30
```

Different `realsense-ros` ROS1 versions may have small `rs_camera.launch` argument-name differences. `d455_color.launch` uses common ros1-legacy names.

## 8. Model Profiles

Model profiles live in:

```text
src/yolo_ros/config/model_profiles/
```

Profile schema:

```yaml
model:
  family: ultralytics
  version: "11"
  task: detect
  backend: engine
  path: /home/bdi/models/yolo11n_fp16.engine
  imgsz: 640
  class_names: coco
  meta: /home/bdi/models/yolo11n_fp16.engine.meta.yaml
  status: stable
  note: ""

inference:
  conf: 0.25
  iou: 0.45
  classes: []
  max_det: 300

external:
  yolov5_repo: ""

ros:
  image_topic: /camera/color/image_raw
  camera_info_topic: /camera/color/camera_info
  detections_topic: /yolo/detections
  overlay_topic: /yolo/overlay
  publish_overlay: true
  queue_size: 1
```

Export parameters and inference parameters are intentionally separated. Runtime profiles describe inference. Export profiles under `tools/export/export_profiles/` describe model conversion.

Inspect a profile:

```bash
python3 tools/diagnostics/inspect_model_profile.py \
  src/yolo_ros/config/model_profiles/yolo11_detect_engine.yaml
```

When `model.meta` points to a sidecar file, the node checks family, task, backend/format, static input size, and selected NMS/end2end flags. Missing sidecar metadata produces a warning, not a startup failure.

## 9. Export Models

Ultralytics-family ONNX export:

```bash
python3 tools/export/export_ultralytics.py \
  --model /home/bdi/models/yolo11n.pt \
  --format onnx \
  --out-dir /home/bdi/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp32 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0
```

Ultralytics-family TensorRT FP16 static engine export:

```bash
python3 tools/export/export_ultralytics.py \
  --model /home/bdi/models/yolo11n.pt \
  --format engine \
  --out-dir /home/bdi/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --device 0 \
  --accelerator gpu
```

Ultralytics-family TensorRT DLA0 FP16 engine export:

```bash
python3 tools/export/export_ultralytics.py \
  --model /home/bdi/models/yolo11n.pt \
  --format engine \
  --out-dir /home/bdi/models \
  --imgsz 640 \
  --batch 1 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --nms false \
  --end2end none \
  --accelerator dla \
  --dla-core 0 \
  --allow-gpu-fallback true
```

INT8 requires representative calibration data:

```bash
python3 tools/export/export_ultralytics.py \
  --model /home/bdi/models/yolo11n.pt \
  --format engine \
  --out-dir /home/bdi/models \
  --imgsz 640 \
  --batch 1 \
  --precision int8 \
  --dynamic true \
  --workspace-gib 4 \
  --data /home/bdi/datasets/coco.yaml \
  --fraction 1.0 \
  --device 0 \
  --accelerator gpu
```

YOLOv5 classic export through an external official repo:

```bash
git clone https://github.com/ultralytics/yolov5 /home/bdi/thirdparty/yolov5

python3 tools/export/export_yolov5_classic.py \
  --yolov5-repo /home/bdi/thirdparty/yolov5 \
  --weights /home/bdi/models/yolov5s.pt \
  --include engine \
  --imgsz 640 \
  --device 0 \
  --precision fp16 \
  --dynamic false \
  --workspace-gib 4 \
  --simplify false \
  --out-dir /home/bdi/models
```

Every export tool writes a sidecar metadata file next to the artifact, for example:

```text
/home/bdi/models/yolo11n_fp16.engine.meta.yaml
```

`trtexec` fallback / diagnostic engine build:

```bash
python3 tools/export/build_engine_trtexec.py \
  --onnx /home/bdi/models/yolo11n.onnx \
  --engine /home/bdi/models/yolo11n_trtexec_fp16.engine \
  --precision fp16 \
  --workspace-gib 4 \
  --input-name images \
  --min-shape 1x3x640x640 \
  --opt-shape 1x3x640x640 \
  --max-shape 1x3x640x640
```

`trtexec` DLA fallback / diagnostic engine build:

```bash
python3 tools/export/build_engine_trtexec.py \
  --onnx /home/bdi/models/yolo11n.onnx \
  --engine /home/bdi/models/yolo11n_dla0_trtexec_fp16.engine \
  --precision fp16 \
  --workspace-gib 4 \
  --input-name images \
  --min-shape 1x3x640x640 \
  --opt-shape 1x3x640x640 \
  --max-shape 1x3x640x640 \
  --use-dla-core 0 \
  --allow-gpu-fallback
```

`trtexec` is a fallback and diagnostic tool, not the default recommended path. A `trtexec` engine is not guaranteed to be parsed correctly by `UltralyticsRunner` or `Yolov5ClassicRunner`. If you use a `trtexec` engine, verify output schema, NMS/end2end state, preprocessing, and postprocessing compatibility. `trtexec` DLA is also fallback / diagnostic; prefer the model family's official export path first.

## 10. Run YOLO Node

Run `yolo_ros` against any image topic:

```bash
roslaunch yolo_ros detect.launch \
  image_topic:=/camera/color/image_raw \
  camera_info_topic:=/camera/color/camera_info \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_engine.yaml
```

Use another camera by changing only `image_topic` and optionally `camera_info_topic`.

Outputs:

```text
/yolo/detections  vision_msgs/Detection2DArray
/yolo/overlay     sensor_msgs/Image, when publish_overlay=true
```

## 11. Run D455 + YOLO Pipeline

Start D455 color and YOLO in one launch:

```bash
roslaunch realsense_camera d455_yolo.launch \
  model_profile:=$(rospack find yolo_ros)/config/model_profiles/yolo11_detect_engine.yaml
```

This is a convenience pipeline. It does not mean `yolo_ros` depends on RealSense.

## 12. Parameters

`detect.launch` arguments:

| Argument | Default |
| --- | --- |
| `model_profile` | `$(find yolo_ros)/config/model_profiles/yolo11_detect_pt.yaml` |
| `image_topic` | `/camera/color/image_raw` |
| `camera_info_topic` | `/camera/color/camera_info` |
| `detections_topic` | `/yolo/detections` |
| `overlay_topic` | `/yolo/overlay` |
| `publish_overlay` | `true` |

Profile inference parameters:

| Parameter | Meaning |
| --- | --- |
| `inference.conf` | Confidence threshold. |
| `inference.iou` | IoU threshold for NMS in the official runtime path. |
| `inference.classes` | Optional class id filter, empty list means all classes. |
| `inference.max_det` | Maximum detections per image. |

Export precision uses:

```text
precision: fp32 | fp16 | int8
```

The export scripts map this internally to official runtime arguments such as `half=True` or `int8=True`.

Engine profile parameters:

| Parameter | Meaning |
| --- | --- |
| `engine.accelerator` | `gpu` or `dla`. |
| `engine.dla_core` | `null`, `0`, or `1`. Orin NX 8GB exposes only DLA core 0; Orin NX 16GB can use core 0 or 1. |
| `engine.precision` | `fp32`, `fp16`, or `int8`. DLA supports only `fp16` and `int8`. |
| `engine.allow_gpu_fallback` | Whether TensorRT may run unsupported DLA layers on GPU. |
| `engine.nms` | Whether export contains NMS. |
| `engine.end2end` | End-to-end export flag when applicable. |

## 13. Camera Topic Requirements

Minimum requirement:

- A ROS `sensor_msgs/Image` topic.

Recommended:

- A matching `sensor_msgs/CameraInfo` topic.

The default tested RealSense D455 topics are:

```text
/camera/color/image_raw
/camera/color/camera_info
```

No depth image, point cloud, aligned depth, or IMU topic is required for `yolo_ros`.

## 14. TensorRT Notes

TensorRT engines are not portable model files. Build the `.engine` on the final deployment Jetson whenever possible.

Do not assume that an engine built on one Jetson, JetPack, TensorRT, CUDA, GPU architecture, or driver stack will work on another device.

Recommended default for Jetson deployment:

- FP16 static TensorRT engine.
- Build with the model family's official export tool first.
- Keep the generated `.meta.yaml` sidecar with the model artifact.

INT8 notes:

- Use representative calibration data from the real deployment scene.
- Poor or mismatched calibration data can reduce accuracy.
- Dynamic shape behavior may be required or enabled by the exporter.

End-to-end / NMS-free notes:

- Some newer exports can include NMS or use end-to-end outputs.
- The runner and metadata must agree on `nms` and `end2end` behavior.
- Verify output schema before deployment.

## 15. DLA Notes

DLA is supported as a TensorRT engine accelerator/export target. It does not change the `yolo_ros` runtime architecture and does not introduce DeepStream.

DLA constraints:

- DLA supports FP16 and INT8 only.
- DLA engines should be built on the final deployment Jetson.
- On Orin NX 8GB use `dla_core=0`; on Orin NX 16GB, `dla_core=0` or `dla_core=1` may be available.
- DLA's main value is lower power, freeing the GPU, and improving multi-stream or multi-model throughput.
- DLA does not guarantee lower single-frame latency than GPU TensorRT.
- If GPU fallback is enabled, some layers may run on GPU.

Ultralytics CLI DLA example:

```bash
yolo export model=yolo11n.pt format=engine device="dla:0" half=True
```

Ultralytics Python DLA example:

```python
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
model.export(format="engine", device="dla:0", half=True)
```

This project does not promise stable DLA support for YOLOv5 classic or YOLOv13. Treat those combinations as experimental and verify the exported engine, output schema, NMS/end2end behavior, and runtime logs.

## 16. Known Limitations

- ROS 2 is not supported.
- Only 2D detect is implemented.
- Segmentation, pose, OBB, classification, depth fusion, point clouds, and 3D detection are not implemented.
- No custom raw TensorRT tensor decoder is included.
- YOLOv5 classic requires an external `ultralytics/yolov5` clone.
- YOLOv13 is experimental and depends on third-party upstream compatibility.
- DLA is supported only as a TensorRT engine export/runtime target, not as a separate DeepStream pipeline.
- RealSense support depends on the official `realsense2_camera` ROS1 wrapper being installed or built.
- RealSense launch arguments may need small adjustments across `realsense-ros` ROS1 wrapper versions.
