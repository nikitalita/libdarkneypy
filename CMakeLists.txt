cmake_minimum_required(VERSION 3.4...3.18)
project(cmake_example)

add_subdirectory(pybind11)
if(APPLE)
  # libomp 15.0+ from brew is keg-only, so have to search in other locations.
  # See https://github.com/Homebrew/homebrew-core/issues/112107#issuecomment-1278042927.
  execute_process(COMMAND brew --prefix libomp
                  OUTPUT_VARIABLE HOMEBREW_LIBOMP_PREFIX
                  OUTPUT_STRIP_TRAILING_WHITESPACE)
  set(OpenMP_C_FLAGS "-Xpreprocessor -fopenmp -I${HOMEBREW_LIBOMP_PREFIX}/include")
  set(OpenMP_CXX_FLAGS "-Xpreprocessor -fopenmp -I${HOMEBREW_LIBOMP_PREFIX}/include")
  set(OpenMP_C_LIB_NAMES omp)
  set(OpenMP_CXX_LIB_NAMES omp)
  set(OpenMP_omp_LIBRARY ${HOMEBREW_LIBOMP_PREFIX}/lib/libomp.dylib)
  find_package(OpenMP)
  if(NOT OPENMP_FOUND)
    message(STATUS "  ->  To enable OpenMP on macOS, please install libomp from Homebrew")
  endif()
else()
  find_package(OpenMP)
endif()

pybind11_add_module(cmake_example src/main.cpp)
find_package(Darknet CONFIG REQUIRED)
target_link_libraries(cmake_example PRIVATE Darknet::dark)

# EXAMPLE_VERSION_INFO is defined by setup.py and passed into the C++ code as a
# define (VERSION_INFO) here.
target_compile_definitions(cmake_example
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})
