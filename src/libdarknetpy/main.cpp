#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl_bind.h>
#include <pybind11/pytypes.h>
#include <array>
#include <pybind11/stl.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>
#define OPENCV 1
#include "yolo_v2_class.hpp"
#include "stb_image.h"

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;
std::vector<bbox_t> (Detector::*detect_1)(std::string, float, bool) = &Detector::detect;
std::vector<bbox_t> (Detector::*detect_2)(image_t, float, bool) = &Detector::detect;
#ifdef OPENCV
std::vector<bbox_t> (Detector::*detect_3)(cv::Mat, float, bool) = &Detector::detect;
#endif

void raw_data_to_image_t(image_t &ret_im, const uint8_t *indata, size_t size)
{
    if (!size)
    {
        ret_im.data = nullptr;
        ret_im.h = 0;
        ret_im.w = 0;
        ret_im.c = 0;
        return;
    }
    int h, w, c = 0;
    auto *data = stbi_load_from_memory(indata, size, &h, &w, &c, 3);

    int i, j, k;
    ret_im.data = (float *)calloc(h * w * c, sizeof(float));
    if (!ret_im.data)
        throw std::runtime_error("Can't allocate image data");
    ret_im.h = h;
    ret_im.w = w;
    ret_im.c = c;
    for (k = 0; k < c; ++k)
    {
        for (j = 0; j < h; ++j)
        {
            for (i = 0; i < w; ++i)
            {
                int dst_index = i + w * j + w * h * k;
                int src_index = k + c * i + c * w * j;
                ret_im.data[dst_index] = (float)data[src_index] / 255.;
            }
        }
    }
    free(data);
}

void raw_data_to_image_t_vec(image_t &ret_im, const std::vector<uint8_t> &vdata)
{
    raw_data_to_image_t(ret_im, vdata.data(), vdata.size());
}

PYBIND11_MODULE(_libdarknetpy, m)
{
    m.doc() = "libdarknetpy module";
    m.def("get_device_count", &get_device_count, "Get the number of available GPUs");
    m.def("get_device_name", &get_device_name, py::arg("gpu"), py::arg("deviceName"), "Get the name of a GPU by index");
    m.def("built_with_cuda", &built_with_cuda, "Check if the library was built with CUDA support");
    m.def("built_with_cudnn", &built_with_cudnn, "Check if the library was built with cuDNN support");
    m.def("built_with_opencv", &built_with_opencv, "Check if the library was built with OpenCV support");
    m.def("send_json_custom", &send_json_custom, py::arg("send_buf"), py::arg("port"), py::arg("timeout"), "Send a JSON string over a socket");

    py::class_<bbox_t>(m, "bbox_t")
        .def_readwrite("x", &bbox_t::x)
        .def_readwrite("y", &bbox_t::y)
        .def_readwrite("w", &bbox_t::w)
        .def_readwrite("h", &bbox_t::h)
        .def_readwrite("prob", &bbox_t::prob)
        .def_readwrite("obj_id", &bbox_t::obj_id)
        .def_readwrite("track_id", &bbox_t::track_id)
        .def_readwrite("frames_counter", &bbox_t::frames_counter)
        .def_readwrite("x_3d", &bbox_t::x_3d)
        .def_readwrite("y_3d", &bbox_t::y_3d)
        .def_readwrite("z_3d", &bbox_t::z_3d);

    py::class_<image_t>(m, "image_t")
        .def("__init__", &raw_data_to_image_t_vec, py::arg("vdata") = std::vector<uint8_t>())
        .def_readwrite("w", &image_t::w)
        .def_readwrite("h", &image_t::h)
        .def_readwrite("c", &image_t::c);

    py::class_<Detector>(m, "Detector")
        .def_readonly("cur_gpu_id", &Detector::cur_gpu_id)
        .def_readwrite("nms", &Detector::nms)
        .def_readwrite("wait_stream", &Detector::wait_stream)
        .def(py::init<std::string, std::string, int, int>(),
             py::arg("configurationFilename"), py::arg("weightsFilename"), py::arg("gpu") = 0, py::arg("batch_size") = 1)
        .def("detect", detect_1, py::arg("image_filename"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)
        .def("detect", detect_2, py::arg("img"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)
        .def("detectBatch", &Detector::detectBatch, py::arg("img"), py::arg("batch_size"), py::arg("width"), py::arg("height"), py::arg("thresh"), py::arg("make_nms") = true)
        .def_static("load_image", &Detector::load_image, py::arg("image_filename"))
        .def_static("free_image", &Detector::free_image, py::arg("m"))
        .def("get_net_width", &Detector::get_net_width)
        .def("get_net_height", &Detector::get_net_height)
        .def("get_net_color_depth", &Detector::get_net_color_depth)
        .def("tracking_id", &Detector::tracking_id, py::arg("cur_bbox_vec"), py::arg("change_history") = true, py::arg("frames_story") = 5, py::arg("max_dist") = 40)
        // wrapper function for above
        .def(
            "detect_raw", [](Detector &d, const std::vector<uint8_t> &vdata, float thresh = 0.2, bool use_mean = false)
            {
#ifdef OPENCV
                cv::Mat mat = imdecode(cv::Mat(vdata), 1);
                return d.detect(mat, thresh, use_mean);
#else
                image_t im;
                raw_data_to_image_t_vec(im, vdata);
                return d.detect(mat, thresh, use_mean);
#endif
            },
            py::arg("vdata"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)

        // .def("get_cuda_context", &Detector::get_cuda_context)
        ;
#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}
