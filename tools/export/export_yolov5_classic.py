#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

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


def export_help(repo: Path) -> str:
    completed = subprocess.run(
        [sys.executable, "export.py", "--help"],
        cwd=str(repo),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def resolve_output(weights: Path, out_dir: Path, include: str) -> Path:
    suffix = ".engine" if include == "engine" else ".onnx"
    candidates = list(weights.parent.glob(f"{weights.stem}*{suffix}")) + list(out_dir.glob(f"{weights.stem}*{suffix}"))
    for candidate in candidates:
        if candidate.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            destination = out_dir / candidate.name
            if candidate.resolve() != destination.resolve():
                shutil.move(str(candidate), str(destination))
            return destination
    raise RuntimeError(f"Could not locate YOLOv5 exported {include} artifact for {weights}")


def write_metadata(path: Path, args: argparse.Namespace) -> None:
    metadata: Dict[str, Any] = {
        "model": {
            "family": "yolov5_classic",
            "version": "5",
            "task": "detect",
            "source": str(Path(args.weights).expanduser()),
            "output": str(path),
        },
        "engine": {
            "format": args.include,
            "precision": args.precision,
            "imgsz": args.imgsz,
            "batch": 1,
            "dynamic": args.dynamic,
            "workspace_gib": args.workspace_gib,
            "nms": False,
            "end2end": None,
            "device": args.device,
        },
        "platform": {
            "jetpack": os.environ.get("JETPACK_VERSION", "unknown"),
            "l4t": command_output(["bash", "-lc", "test -r /etc/nv_tegra_release && cat /etc/nv_tegra_release"]),
            "tensorrt": command_output(["trtexec", "--version"]),
            "cuda": command_output(["nvcc", "--version"]),
        },
        "runtime": {
            "expected_runner": "yolov5_classic_runner",
        },
    }
    meta_path = Path(f"{path}.meta.yaml")
    with meta_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, sort_keys=False)
    print(f"Wrote metadata: {meta_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export YOLOv5 classic models by invoking ultralytics/yolov5/export.py.")
    parser.add_argument("--yolov5-repo", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--include", required=True, choices=["onnx", "engine"])
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--precision", choices=["fp32", "fp16"], default="fp16")
    parser.add_argument("--dynamic", type=str_to_bool, default=False)
    parser.add_argument("--workspace-gib", type=float, default=4)
    parser.add_argument("--simplify", type=str_to_bool, default=False)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    repo = Path(args.yolov5_repo).expanduser()
    weights = Path(args.weights).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    export_py = repo / "export.py"
    if not export_py.exists():
        raise SystemExit(f"YOLOv5 export.py not found: {export_py}. Clone https://github.com/ultralytics/yolov5 first.")
    if not weights.exists():
        raise SystemExit(f"Weights file not found: {weights}")

    help_text = export_help(repo)
    command = [
        sys.executable,
        "export.py",
        "--weights",
        str(weights),
        "--include",
        args.include,
        "--imgsz",
        str(args.imgsz),
        "--device",
        str(args.device),
    ]
    if args.precision == "fp16":
        command.append("--half")
    if args.dynamic:
        command.append("--dynamic")
    if args.simplify:
        command.append("--simplify")
    if "--workspace" in help_text:
        command.extend(["--workspace", str(args.workspace_gib)])
    elif args.include == "engine":
        print("WARNING: this YOLOv5 export.py does not advertise --workspace; continuing without it.", file=sys.stderr)

    print("Running:", " ".join(command))
    try:
        subprocess.run(command, cwd=str(repo), check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"YOLOv5 export.py failed with exit code {exc.returncode}") from exc

    output = resolve_output(weights, out_dir, args.include)
    print(f"Exported artifact: {output}")
    write_metadata(output, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

