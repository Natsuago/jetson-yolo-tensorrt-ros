#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


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


def build_command(args: argparse.Namespace) -> List[str]:
    command = [
        "trtexec",
        f"--onnx={args.onnx}",
        f"--saveEngine={args.engine}",
        f"--memPoolSize=workspace:{args.workspace_gib}G",
    ]
    if args.precision == "fp16":
        command.append("--fp16")
    elif args.precision == "int8":
        command.append("--int8")
        if args.calib_cache:
            command.append(f"--calib={args.calib_cache}")
    if args.use_dla_core is not None:
        command.append(f"--useDLACore={args.use_dla_core}")
    if args.allow_gpu_fallback:
        command.append("--allowGPUFallback")

    if args.input_name and args.min_shape and args.opt_shape and args.max_shape:
        command.extend(
            [
                f"--minShapes={args.input_name}:{args.min_shape}",
                f"--optShapes={args.input_name}:{args.opt_shape}",
                f"--maxShapes={args.input_name}:{args.max_shape}",
            ]
        )
    return command


def write_metadata(args: argparse.Namespace) -> None:
    output = Path(args.engine).expanduser()
    metadata: Dict[str, Any] = {
        "model": {
            "family": args.family,
            "version": args.version,
            "task": "detect",
            "source": str(Path(args.onnx).expanduser()),
            "output": str(output),
        },
        "engine": {
            "format": "engine",
            "accelerator": "dla" if args.use_dla_core is not None else "gpu",
            "dla_core": args.use_dla_core,
            "precision": args.precision,
            "imgsz": args.imgsz,
            "batch": 1,
            "dynamic": args.min_shape != args.max_shape,
            "workspace_gib": args.workspace_gib,
            "allow_gpu_fallback": args.allow_gpu_fallback,
            "nms": None,
            "end2end": None,
            "device": "trtexec",
        },
        "platform": {
            "jetpack": os.environ.get("JETPACK_VERSION", "unknown"),
            "l4t": command_output(["bash", "-lc", "test -r /etc/nv_tegra_release && cat /etc/nv_tegra_release"]),
            "tensorrt": command_output(["trtexec", "--version"]),
            "cuda": command_output(["nvcc", "--version"]),
        },
        "runtime": {
            "expected_runner": "verify_manually",
        },
    }
    meta_path = Path(f"{output}.meta.yaml")
    with meta_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)
    print(f"Wrote metadata: {meta_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fallback diagnostic TensorRT engine builder using trtexec.")
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--precision", choices=["fp32", "fp16", "int8"], default="fp16")
    parser.add_argument("--workspace-gib", type=float, default=4)
    parser.add_argument("--input-name", default="images")
    parser.add_argument("--min-shape", default="1x3x640x640")
    parser.add_argument("--opt-shape", default="1x3x640x640")
    parser.add_argument("--max-shape", default="1x3x640x640")
    parser.add_argument("--calib-cache", default=None)
    parser.add_argument("--use-dla-core", type=int, default=None)
    parser.add_argument("--allow-gpu-fallback", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--family", default="unknown")
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()
    if args.use_dla_core is not None:
        if args.use_dla_core not in {0, 1}:
            parser.error("--use-dla-core must be 0 or 1. Orin NX 8GB exposes only DLA core 0.")
        if args.precision not in {"fp16", "int8"}:
            parser.error("DLA requires --precision fp16 or --precision int8.")

    command = build_command(args)
    print(" ".join(command))
    if args.dry_run:
        return 0

    Path(args.engine).expanduser().parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit("trtexec not found in PATH. Install TensorRT tools or source the correct environment.") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"trtexec failed with exit code {exc.returncode}") from exc

    write_metadata(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
