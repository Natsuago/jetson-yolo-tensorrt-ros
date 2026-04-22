#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def add_package_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    package_src = repo_root / "src" / "yolo_ros" / "src"
    sys.path.insert(0, str(package_src))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and validate a yolo_ros model profile.")
    parser.add_argument("profile")
    args = parser.parse_args()

    add_package_path()
    from yolo_ros.core.model_profile import ModelProfile, check_metadata_compatibility

    warnings = []
    infos = []
    profile = ModelProfile.from_file(args.profile)
    check_metadata_compatibility(profile, warnings.append, infos.append)

    print(f"profile: {profile.source_path}")
    print(f"family: {profile.model.family}")
    print(f"version: {profile.model.version}")
    print(f"task: {profile.model.task}")
    print(f"backend: {profile.model.backend}")
    print(f"model path: {profile.model.path}")
    print(f"imgsz: {profile.model.imgsz}")
    print(f"detections topic: {profile.ros.detections_topic}")
    print(f"overlay: {profile.ros.publish_overlay} -> {profile.ros.overlay_topic}")
    if profile.engine is not None:
        print(f"engine accelerator: {profile.engine.accelerator}")
        print(f"engine dla_core: {profile.engine.dla_core}")
        print(f"engine precision: {profile.engine.precision}")
        print(f"engine allow_gpu_fallback: {profile.engine.allow_gpu_fallback}")
    for info in infos:
        print(f"INFO: {info}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
