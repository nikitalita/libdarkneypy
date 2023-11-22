"""
libdarknetpy module
"""
from __future__ import annotations
import typing
__all__ = ['Detector', 'bbox_t', 'built_with_cuda', 'built_with_cudnn', 'built_with_opencv', 'get_device_count', 'get_device_name', 'image_t', 'send_json_custom']
class Detector:
    nms: float
    wait_stream: bool
    @staticmethod
    def free_image(m: image_t) -> None:
        ...
    @staticmethod
    def load_image(image_filename: str) -> image_t:
        ...
    def __init__(self, configurationFilename: str, weightsFilename: str, gpu: int = 0, batch_size: int = 1) -> None:
        ...
    @typing.overload
    def detect(self, image_filename: str, thresh: float = 0.2, use_mean: bool = False) -> list[bbox_t]:
        ...
    @typing.overload
    def detect(self, img: image_t, thresh: float = 0.2, use_mean: bool = False) -> list[bbox_t]:
        ...
    def detectBatch(self, img: image_t, batch_size: int, width: int, height: int, thresh: float, make_nms: bool = True) -> list[list[bbox_t]]:
        ...
    def detect_raw(self, vdata: list[int]) -> list[bbox_t]:
        ...
    def get_cuda_context(self) -> capsule:
        ...
    def get_net_color_depth(self) -> int:
        ...
    def get_net_height(self) -> int:
        ...
    def get_net_width(self) -> int:
        ...
    def tracking_id(self, cur_bbox_vec: list[bbox_t], change_history: bool = True, frames_story: int = 5, max_dist: int = 40) -> list[bbox_t]:
        ...
    @property
    def cur_gpu_id(self) -> int:
        ...
class bbox_t:
    frames_counter: int
    h: int
    obj_id: int
    prob: float
    track_id: int
    w: int
    x: int
    x_3d: float
    y: int
    y_3d: float
    z_3d: float
class image_t:
    c: int
    h: int
    w: int
    def __init__(self, vdata: list[int] = []) -> None:
        ...
def built_with_cuda() -> bool:
    """
    Check if the library was built with CUDA support
    """
def built_with_cudnn() -> bool:
    """
    Check if the library was built with cuDNN support
    """
def built_with_opencv() -> bool:
    """
    Check if the library was built with OpenCV support
    """
def get_device_count() -> int:
    """
    Get the number of available GPUs
    """
def get_device_name(gpu: int, deviceName: str) -> int:
    """
    Get the name of a GPU by index
    """
def send_json_custom(send_buf: str, port: int, timeout: int) -> None:
    """
    Send a JSON string over a socket
    """
__version__: str = '0.0.1'
