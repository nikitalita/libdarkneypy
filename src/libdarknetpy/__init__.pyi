"""

libdarknetpy: A Pybind11-based Python wrapper for darknet.
"""
from __future__ import annotations

from libdarknetpy._libdarknetpy import (
    Detector,
    bbox_t,
    built_with_cuda,
    built_with_cudnn,
    built_with_opencv,
    get_device_count,
    get_device_name,
    image_t,
    send_json_custom,
)

__all__ = [
    "Detector",
    "bbox_t",
    "built_with_cuda",
    "built_with_cudnn",
    "built_with_opencv",
    "get_device_count",
    "get_device_name",
    "image_t",
    "send_json_custom",
]
