#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


def str_to_bool(value: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected true or false, got {value!r}")


def command_output(command) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else "unknown"
    except FileNotFoundError:
        return "unknown"


def infer_family_version(model_path: Path) -> Tuple[str, str]:
    name = model_path.stem.lower()
    if "13" in name:
        return "yolov13", "13"
    for version in ("26", "12", "11", "8"):
        if f"yolo{version}" in name or f"yolov{version}" in name:
            return "ultralytics", version
    return "ultralytics", "unknown"


def resolve_output(result: Any, model_path: Path, out_dir: Path, export_format: str) -> Path:
    candidates = []
    if result:
        if isinstance(result, (list, tuple)):
            candidates.extend(Path(item).expanduser() for item in result)
        else:
            candidates.append(Path(str(result)).expanduser())

    suffix = ".engine" if export_format == "engine" else ".onnx"
    candidates.extend(model_path.parent.glob(f"{model_path.stem}*{suffix}"))
    candidates.extend(out_dir.glob(f"{model_path.stem}*{suffix}"))

    for candidate in candidates:
        if candidate.exists() and candidate.suffix == suffix:
            out_dir.mkdir(parents=True, exist_ok=True)
            destination = out_dir / candidate.name
            if candidate.resolve() != destination.resolve():
                shutil.move(str(candidate), str(destination))
            return destination

    raise RuntimeError(f"Could not locate exported {export_format} artifact for {model_path}")


def artifact_suffix(args: argparse.Namespace) -> str:
    if args.format == "engine":
        if args.accelerator == "dla":
            return f"dla{args.dla_core}_{args.precision}"
        return f"gpu_{args.precision}"
    return args.format


def canonicalize_output_name(output: Path, model_path: Path, args: argparse.Namespace) -> Path:
    suffix = artifact_suffix(args)
    desired = output.with_name(f"{model_path.stem}_{suffix}{output.suffix}")
    if output.resolve() == desired.resolve():
        return output
    if desired.exists():
        desired.unlink()
    output.rename(desired)
    return desired


def write_metadata(path: Path, args: argparse.Namespace, output: Path) -> None:
    family, version = infer_family_version(Path(args.model))
    precision = args.precision
    dla_core = args.dla_core if args.accelerator == "dla" else None
    allow_gpu_fallback = args.allow_gpu_fallback if args.accelerator == "dla" else False
    metadata: Dict[str, Any] = {
        "model": {
            "family": family,
            "version": version,
            "task": "detect",
            "source": str(Path(args.model).expanduser()),
            "output": str(output),
        },
        "engine": {
            "format": args.format,
            "accelerator": args.accelerator,
            "dla_core": dla_core,
            "precision": precision,
            "imgsz": args.imgsz,
            "batch": args.batch,
            "dynamic": args.dynamic,
            "workspace_gib": args.workspace_gib,
            "allow_gpu_fallback": allow_gpu_fallback,
            "nms": args.nms,
            "end2end": None if args.end2end == "none" else str_to_bool(args.end2end),
            "device": args.export_device,
        },
        "platform": {
            "jetpack": os.environ.get("JETPACK_VERSION", "unknown"),
            "l4t": command_output(["bash", "-lc", "test -r /etc/nv_tegra_release && cat /etc/nv_tegra_release"]),
            "tensorrt": command_output(["trtexec", "--version"]),
            "cuda": command_output(["nvcc", "--version"]),
        },
        "runtime": {
            "expected_runner": "ultralytics_runner",
        },
    }
    meta_path = Path(f"{path}.meta.yaml")
    with meta_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)
    print(f"Wrote metadata: {meta_path}")


def build_export_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    half = args.precision == "fp16"
    int8 = args.precision == "int8"
    kwargs: Dict[str, Optional[Any]] = {
        "format": args.format,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "half": half,
        "int8": int8,
        "dynamic": args.dynamic,
        "workspace": args.workspace_gib,
        "simplify": args.simplify,
        "nms": args.nms,
        "device": args.export_device,
        "data": args.data,
        "fraction": args.fraction,
    }
    if args.end2end != "none":
        kwargs["end2end"] = str_to_bool(args.end2end)
    return {key: value for key, value in kwargs.items() if value is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Ultralytics-family YOLO detect models to ONNX or TensorRT engine.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--format", required=True, choices=["onnx", "engine"])
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--precision", choices=["fp32", "fp16", "int8"], default="fp16")
    parser.add_argument("--dynamic", type=str_to_bool, default=False)
    parser.add_argument("--workspace-gib", type=float, default=4)
    parser.add_argument("--simplify", type=str_to_bool, default=False)
    parser.add_argument("--nms", type=str_to_bool, default=False)
    parser.add_argument("--end2end", choices=["true", "false", "none"], default="none")
    parser.add_argument("--device", default="0")
    parser.add_argument("--accelerator", choices=["gpu", "dla"], default="gpu")
    parser.add_argument("--dla-core", type=int, default=0)
    parser.add_argument("--allow-gpu-fallback", type=str_to_bool, default=True)
    parser.add_argument("--data", default=None)
    parser.add_argument("--fraction", type=float, default=1.0)
    args = parser.parse_args()

    if args.accelerator == "dla":
        if args.format != "engine":
            parser.error("accelerator=dla requires --format engine.")
        if args.precision not in {"fp16", "int8"}:
            parser.error("accelerator=dla supports only --precision fp16 or --precision int8.")
        if args.dla_core not in {0, 1}:
            parser.error("--dla-core must be 0 or 1. Orin NX 8GB exposes only DLA core 0.")
        args.export_device = f"dla:{args.dla_core}"
    else:
        args.export_device = args.device

    if args.precision == "int8" and not args.data:
        print(
            "WARNING: INT8 export should use a representative deployment dataset via --data. "
            "Calibration quality may be poor without it.",
            file=sys.stderr,
        )
    if args.precision == "int8" and not args.dynamic:
        print("NOTE: Ultralytics TensorRT INT8 export may enable or require dynamic shapes internally.", file=sys.stderr)
    if args.accelerator == "dla":
        print(
            f"NOTE: exporting TensorRT engine for DLA core {args.dla_core} with device={args.export_device}. "
            "DLA supports FP16/INT8 only; unsupported layers may require GPU fallback.",
            file=sys.stderr,
        )
        if "yolo11" in Path(args.model).name.lower():
            print(
                "WARNING: YOLO11 DLA engines are experimental on JetPack 5.1.4 / TensorRT 8.5.2. "
                "This project has observed YOLO11n DLA0 FP16 returning zero detections while "
                "GPU TensorRT FP16 works. Validate the exported engine on a static image before ROS deployment.",
                file=sys.stderr,
            )

    model_path = Path(args.model).expanduser()
    out_dir = Path(args.out_dir).expanduser()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Python package 'ultralytics' is required. Install with: pip3 install ultralytics") from exc

    kwargs = build_export_kwargs(args)
    print(f"Export parameters: {kwargs}")
    model = YOLO(str(model_path))
    result = model.export(**kwargs)
    output = resolve_output(result, model_path, out_dir, args.format)
    output = canonicalize_output_name(output, model_path, args)
    print(f"Exported artifact: {output}")
    write_metadata(output, args, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
