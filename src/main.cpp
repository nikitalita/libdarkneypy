#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "yolo_v2_class.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl_bind.h>
#include <pybind11/embed.h>
#include <pybind11/pytypes.h>
#include <pybind11/numpy.h>
#include <array>
#include <pybind11/stl.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h> 
#include <pybind11/chrono.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;
std::vector<bbox_t> (Detector::*detect_1)(std::string, float, bool) = &Detector::detect;
std::vector<bbox_t> (Detector::*detect_2)(image_t, float, bool) = &Detector::detect;
std::vector<bbox_t> (Detector::*detect_3)(cv::Mat, float, bool) = &Detector::detect;

PYBIND11_MODULE(libdarknetpy, m) {
    m.doc() = "libdarknetpy module";
    m.def("init", &init, py::arg("configurationFilename"), py::arg("weightsFilename"), py::arg("gpu") = 0, py::arg("batch_size") = 1, "Initialize the detector");
    m.def("detect_image", &detect_image, py::arg("filename"), py::arg("container"), "Detect objects in an image");
    m.def("detect_mat", &detect_mat, py::arg("data"), py::arg("data_length"), py::arg("container"), "Detect objects in a resized image");
    m.def("dispose", &dispose, "Dispose the detector");
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
        .def_readwrite("data", &image_t::data)
        .def_readwrite("w", &image_t::w)
        .def_readwrite("h", &image_t::h)
        .def_readwrite("c", &image_t::c);


// bbox_t_container looks like this:
// struct bbox_t_container {
//     bbox_t candidates[C_SHARP_MAX_OBJECTS];
// };
    py::class_<bbox_t_container>(m, "bbox_t_container")
        .def(py::init<>())
        .def_property("candidates", [](bbox_t_container &p)->pybind11::array {
            auto dtype = pybind11::dtype(pybind11::format_descriptor<bbox_t>::format());
            return pybind11::array(
                dtype, 
                { C_SHARP_MAX_OBJECTS }, 
                { sizeof(bbox_t) }, 
                p.candidates, 
                nullptr
            );
            }, [](bbox_t_container& p) {});

    py::class_<Detector>(m, "Detector")
        .def(py::init<std::string, std::string, int, int>())
        .def("detect", detect_1, py::arg("image_filename"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)
        .def("detect", detect_2, py::arg("img"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)
        .def("detectBatch", &Detector::detectBatch, py::arg("img"), py::arg("batch_size"), py::arg("width"), py::arg("height"), py::arg("thresh"), py::arg("make_nms") = true)
        .def_static("load_image", &Detector::load_image, py::arg("image_filename"))
        .def_static("free_image", &Detector::free_image, py::arg("m"))
        .def("get_net_width", &Detector::get_net_width)
        .def("get_net_height", &Detector::get_net_height)
        .def("get_net_color_depth", &Detector::get_net_color_depth)
        .def("tracking_id", &Detector::tracking_id, py::arg("cur_bbox_vec"), py::arg("change_history") = true, py::arg("frames_story") = 5, py::arg("max_dist") = 40)
#ifdef OPENCV
        // .def("detect", detect_3, py::arg("mat"), py::arg("thresh") = 0.2, py::arg("use_mean") = false)
        // wrapper function for above
        .def("detect_raw", [](Detector &d, std::vector<uint8_t> vdata) {
            cv::Mat mat = imdecode(cv::Mat(vdata), 1);
            return d.detect(mat);
        })
#endif
        .def("get_cuda_context", &Detector::get_cuda_context);
#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}