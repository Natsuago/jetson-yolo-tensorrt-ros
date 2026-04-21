#!/usr/bin/env python3
from catkin_pkg.python_setup import generate_distutils_setup
from setuptools import setup

setup_args = generate_distutils_setup(
    packages=[
        "yolo_ros",
        "yolo_ros.node",
        "yolo_ros.core",
        "yolo_ros.providers",
        "yolo_ros.runners",
        "yolo_ros.tasks",
        "yolo_ros.ros",
        "yolo_ros.utils",
    ],
    package_dir={"": "src"},
)

setup(**setup_args)

