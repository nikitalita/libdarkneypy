"""

libdarknetpy: A Pybind11-based Python wrapper for darknet.
"""
from __future__ import annotations
from libdarknetpy._libdarknetpy import Detector
from libdarknetpy._libdarknetpy import bbox_t
from libdarknetpy._libdarknetpy import bbox_t_container
from libdarknetpy._libdarknetpy import built_with_cuda
from libdarknetpy._libdarknetpy import built_with_cudnn
from libdarknetpy._libdarknetpy import built_with_opencv
from libdarknetpy._libdarknetpy import detect_image
from libdarknetpy._libdarknetpy import detect_mat
from libdarknetpy._libdarknetpy import dispose
from libdarknetpy._libdarknetpy import get_device_count
from libdarknetpy._libdarknetpy import get_device_name
from libdarknetpy._libdarknetpy import image_t
from libdarknetpy._libdarknetpy import init
from libdarknetpy._libdarknetpy import send_json_custom
from . import _libdarknetpy
__all__ = ['Detector', 'bbox_t', 'bbox_t_container', 'built_with_cuda', 'built_with_cudnn', 'built_with_opencv', 'detect_image', 'detect_mat', 'dispose', 'get_device_count', 'get_device_name', 'image_t', 'init', 'send_json_custom']
