#!/usr/bin/env bash
set -u

LIBREALSENSE_ROOT="${LIBREALSENSE_ROOT:-/home/bdi/thridprty/librealsense}"
if [[ "${1:-}" == "--librealsense-root" && -n "${2:-}" ]]; then
  LIBREALSENSE_ROOT="$2"
fi

failures=0

check_path() {
  local label="$1"
  local path="$2"
  if [[ -e "$path" ]]; then
    echo "[OK] ${label}: ${path}"
  else
    echo "[MISSING] ${label}: ${path}"
    failures=$((failures + 1))
  fi
}

find_tool() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi
  local candidates=(
    "${LIBREALSENSE_ROOT}/build/tools/${name}"
    "${LIBREALSENSE_ROOT}/build/tools/${name}/${name}"
    "${LIBREALSENSE_ROOT}/build/tools/enumerate-devices/${name}"
    "${LIBREALSENSE_ROOT}/build/tools/realsense-viewer/${name}"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" || -f "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

check_path "librealsense root" "${LIBREALSENSE_ROOT}"
check_path "CMakeLists.txt" "${LIBREALSENSE_ROOT}/CMakeLists.txt"
check_path "build directory" "${LIBREALSENSE_ROOT}/build"
check_path "tools directory" "${LIBREALSENSE_ROOT}/tools"
check_path "wrappers directory" "${LIBREALSENSE_ROOT}/wrappers"

if tool_path="$(find_tool rs-enumerate-devices)"; then
  echo "[OK] rs-enumerate-devices: ${tool_path}"
else
  echo "[MISSING] rs-enumerate-devices"
  failures=$((failures + 1))
fi

if pkg-config --modversion realsense2 >/tmp/realsense2_pkg_config.$$ 2>&1; then
  echo "[OK] pkg-config realsense2: $(cat /tmp/realsense2_pkg_config.$$)"
else
  echo "[MISSING] pkg-config --modversion realsense2: $(cat /tmp/realsense2_pkg_config.$$)"
  failures=$((failures + 1))
fi
rm -f /tmp/realsense2_pkg_config.$$

exit "${failures}"

