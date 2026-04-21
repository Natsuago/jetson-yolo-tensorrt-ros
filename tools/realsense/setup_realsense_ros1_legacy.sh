#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WS_SRC="${REPO_ROOT}/src"
LIBREALSENSE_ROOT="/home/bdi/thridprty/librealsense"
CLONE=false
INSTALL_DEPS=false
BUILD=false
DRY_RUN=false

usage() {
  cat <<'USAGE'
Usage: tools/realsense/setup_realsense_ros1_legacy.sh [options]

Options:
  --librealsense-root PATH   Default: /home/bdi/thridprty/librealsense
  --clone                   Clone IntelRealSense/realsense-ros into src/realsense-ros
  --install-deps            Run apt install for common ROS Noetic dependencies
  --build                   Run catkin_make from repository root
  --dry-run                 Print actions without changing the system
  -h, --help                Show this help
USAGE
}

run_cmd() {
  echo "+ $*"
  if [[ "${DRY_RUN}" == "false" ]]; then
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --librealsense-root)
      LIBREALSENSE_ROOT="$2"
      shift 2
      ;;
    --clone)
      CLONE=true
      shift
      ;;
    --install-deps)
      INSTALL_DEPS=true
      shift
      ;;
    --build)
      BUILD=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

echo "Repository root: ${REPO_ROOT}"
echo "librealsense root: ${LIBREALSENSE_ROOT}"

if rospack find realsense2_camera >/dev/null 2>&1; then
  echo "realsense2_camera is already available: $(rospack find realsense2_camera)"
else
  echo "realsense2_camera is not found. Install ros-noetic-realsense2-camera or build IntelRealSense/realsense-ros ros1-legacy from source."
fi

if [[ -d "${LIBREALSENSE_ROOT}/wrappers/ros" ]]; then
  echo "Found ${LIBREALSENSE_ROOT}/wrappers/ros. You may manually symlink an existing realsense2_camera package if it matches your librealsense source."
elif [[ -d "${LIBREALSENSE_ROOT}/wrappers" ]]; then
  echo "Found librealsense wrappers directory: ${LIBREALSENSE_ROOT}/wrappers"
else
  echo "WARNING: librealsense wrappers directory was not found under ${LIBREALSENSE_ROOT}."
fi

if [[ "${INSTALL_DEPS}" == "true" ]]; then
  run_cmd sudo apt update
  run_cmd sudo apt install -y \
    ros-noetic-ddynamic-reconfigure \
    ros-noetic-diagnostic-updater \
    ros-noetic-image-transport \
    ros-noetic-cv-bridge \
    ros-noetic-tf \
    ros-noetic-tf2-ros \
    ros-noetic-nodelet
else
  cat <<'MSG'
Common dependency command, not executed:
  sudo apt install -y ros-noetic-ddynamic-reconfigure ros-noetic-diagnostic-updater ros-noetic-image-transport ros-noetic-cv-bridge ros-noetic-tf ros-noetic-tf2-ros ros-noetic-nodelet
MSG
fi

if [[ "${CLONE}" == "true" ]]; then
  run_cmd mkdir -p "${WS_SRC}"
  if [[ -d "${WS_SRC}/realsense-ros" ]]; then
    echo "${WS_SRC}/realsense-ros already exists; not cloning again."
  else
    run_cmd git clone --branch ros1-legacy https://github.com/IntelRealSense/realsense-ros.git "${WS_SRC}/realsense-ros"
  fi
else
  echo "Clone step skipped. Pass --clone to fetch IntelRealSense/realsense-ros ros1-legacy."
fi

cat <<'MSG'
Make sure librealsense2 can be found by CMake or pkg-config. If needed, install it or set CMAKE_PREFIX_PATH / LD_LIBRARY_PATH to your librealsense build/install location.
MSG

if [[ "${BUILD}" == "true" ]]; then
  run_cmd bash -lc "cd '${REPO_ROOT}' && catkin_make -DCATKIN_ENABLE_TESTING=False -DCMAKE_BUILD_TYPE=Release"
else
  echo "Build step skipped. Pass --build to run:"
  echo "  catkin_make -DCATKIN_ENABLE_TESTING=False -DCMAKE_BUILD_TYPE=Release"
fi
