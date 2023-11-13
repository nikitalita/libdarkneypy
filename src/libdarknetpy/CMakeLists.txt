
#add_subdirectory(pybind11)
# run `pybind11-config --cmakedir` in shell

find_package(pybind11 QUIET)
if(NOT pybind11_FOUND)
  set(PYBIND_CONFIG_CMD "pybind11-config --cmakedir")
  execute_process(COMMAND "pybind11-config" "--cmakedir"
                  OUTPUT_VARIABLE PYBIND11_DIR
                  OUTPUT_STRIP_TRAILING_WHITESPACE)
  set(pybind11_DIR ${PYBIND11_DIR})
  message("pybind11_DIR: ${pybind11_DIR}")
endif()

find_package(pybind11 CONFIG REQUIRED)
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

find_package(Darknet CONFIG REQUIRED)
pybind11_add_module(_libdarknetpy main.cpp)
target_link_libraries(_libdarknetpy PRIVATE Darknet::dark)

if(UNIX AND NOT (CMAKE_CXX_COMPILER_ID MATCHES "Clang"))
  set(SHAREDLIB_CXX_FLAGS "-Wl,-Bsymbolic")
  set(SHAREDLIB_C_FLAGS "-Wl,-Bsymbolic")
endif()

set(CMAKE_CXX_FLAGS "${SHAREDLIB_CXX_FLAGS} ${CMAKE_CXX_FLAGS}")
set(CMAKE_C_FLAGS "${SHAREDLIB_C_FLAGS} ${CMAKE_C_FLAGS}")
#add -Wl,-Bsymbolic to CMAKE_CXX_FLAGS  and CMAKE_C_FLAGS flags

# EXAMPLE_VERSION_INFO is defined by setup.py and passed into the C++ code as a
# define (VERSION_INFO) here.
target_compile_definitions(_libdarknetpy
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})
