#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from typing import Iterable, Tuple


def run(command: Iterable[str]) -> Tuple[bool, str]:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return completed.returncode == 0, completed.stdout.strip()
    except FileNotFoundError as exc:
        return False, str(exc)


def print_status(label: str, ok: bool, detail: str = "") -> None:
    prefix = "OK" if ok else "MISSING"
    if detail:
        print(f"[{prefix}] {label}: {detail}")
    else:
        print(f"[{prefix}] {label}")


def module_status(name: str) -> None:
    spec = importlib.util.find_spec(name)
    print_status(f"python module {name}", spec is not None)


def main() -> int:
    failures = 0
    print(f"Python: {sys.version.split()[0]}")
    print(f"ROS_DISTRO: {os.environ.get('ROS_DISTRO', 'not set')}")

    checks = [
        ("rospack find vision_msgs", ["rospack", "find", "vision_msgs"]),
        ("trtexec --version", ["trtexec", "--version"]),
        ("nvcc --version", ["nvcc", "--version"]),
    ]
    for label, command in checks:
        ok, output = run(command)
        print_status(label, ok, output.splitlines()[0] if output else "")
        if not ok:
            failures += 1

    for module in ("yaml", "numpy", "cv2", "torch", "ultralytics"):
        spec = importlib.util.find_spec(module)
        print_status(f"python module {module}", spec is not None)
        if spec is None and module in {"yaml", "numpy"}:
            failures += 1

    l4t_ok, l4t = run(["bash", "-lc", "test -r /etc/nv_tegra_release && cat /etc/nv_tegra_release"])
    print_status("L4T release", l4t_ok, l4t)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

