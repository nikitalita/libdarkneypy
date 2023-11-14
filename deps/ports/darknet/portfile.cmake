vcpkg_from_github(
  OUT_SOURCE_PATH SOURCE_PATH
  REPO hank-ai/darknet
  REF 27a4e80b75a463e8bb10e8dd74ce0547d2a1b70c
  SHA512 c79243900a5b0c6dcec1b82c50da2fd12ee6e76fc2a31adbecfced47399ab0f8e9bafe6d656d0de3f9ad69370e6ed78cb1b1d57e082257cbed41151f91400cee
  HEAD_REF master
  PATCHES 0002-fix-dependence-getopt.patch 0003-fix-dependence-libopt-config.patch
)

vcpkg_check_features(OUT_FEATURE_OPTIONS FEATURE_OPTIONS
  FEATURES
    cuda ENABLE_CUDA
    cudnn ENABLE_CUDNN
)

#do not move following features to vcpkg_check_features because they break themselves: one off will turn off the others even if true
set(ENABLE_OPENCV FALSE )
if ("opencv-base" IN_LIST FEATURES OR "opencv2-base" IN_LIST FEATURES OR "opencv3-base" IN_LIST FEATURES OR "opencv-cuda" IN_LIST FEATURES OR "opencv2-cuda" IN_LIST FEATURES OR "opencv3-cuda" IN_LIST FEATURES)
  set(ENABLE_OPENCV TRUE)
endif()

if ("cuda" IN_LIST FEATURES)
  if (NOT VCPKG_CMAKE_SYSTEM_NAME AND NOT ENV{CUDACXX})
    #CMake looks for nvcc only in PATH and CUDACXX env vars for the Ninja generator. Since we filter path on vcpkg and CUDACXX env var is not set by CUDA installer on Windows, CMake cannot find CUDA when using Ninja generator, so we need to manually enlight it if necessary (https://gitlab.kitware.com/cmake/cmake/issues/19173). Otherwise we could just disable Ninja and use MSBuild, but unfortunately CUDA installer does not integrate with some distributions of MSBuild (like the ones inside Build Tools), making CUDA unavailable otherwise in those cases, which we want to avoid
    set(ENV{CUDACXX} "$ENV{CUDA_PATH}/bin/nvcc.exe")
  endif()
endif()

#make sure we don't use any integrated pre-built library nor any unnecessary CMake module
file(REMOVE_RECURSE "${SOURCE_PATH}/3rdparty")
file(REMOVE_RECURSE "${SOURCE_PATH}/cmake/Modules")

# check if the compile target is x86_64 or arm64
# we can just check the target triplet
if (VCPKG_TARGET_TRIPLET MATCHES "x64-.*")
  set(ARCH "x64")
elseif (VCPKG_TARGET_TRIPLET MATCHES "arm64-.*")
  set(ARCH "arm64")
endif()

set(ENABLE_SSE_AND_AVX_FLAGS FALSE)
if (ARCH MATCHES "x64")
  set(ENABLE_SSE_AND_AVX_FLAGS TRUE)
endif()


vcpkg_cmake_configure(
  SOURCE_PATH "${SOURCE_PATH}"
  DISABLE_PARALLEL_CONFIGURE
  OPTIONS ${FEATURE_OPTIONS}
    -DINSTALL_BIN_DIR:STRING=bin
    -DINSTALL_LIB_DIR:STRING=lib
    -DENABLE_OPENCV:BOOL=${ENABLE_OPENCV}
    -DENABLE_SSE_AND_AVX_FLAGS:BOOL=${ENABLE_SSE_AND_AVX_OPTION}
)

vcpkg_cmake_install()
vcpkg_copy_tools(AUTO_CLEAN TOOL_NAMES darknet uselib)
if ("opencv-cuda" IN_LIST FEATURES OR "opencv3-cuda" IN_LIST FEATURES)
  vcpkg_copy_tools(AUTO_CLEAN TOOL_NAMES uselib_track)
endif()

file(COPY "${SOURCE_PATH}/cfg" DESTINATION "${CURRENT_PACKAGES_DIR}/tools/${PORT}")
file(COPY "${SOURCE_PATH}/data" DESTINATION "${CURRENT_PACKAGES_DIR}/tools/${PORT}")

if(VCPKG_LIBRARY_LINKAGE STREQUAL static)
  file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/bin" "${CURRENT_PACKAGES_DIR}/debug/bin")
endif()

vcpkg_cmake_config_fixup()

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/share")
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")

file(INSTALL "${SOURCE_PATH}/scripts/download_weights.ps1" DESTINATION "${CURRENT_PACKAGES_DIR}/tools/${PORT}/scripts")
message(STATUS "To download weight files, please go to ${CURRENT_INSTALLED_DIR}/tools/${PORT}/scripts and run ./download_weights.ps1")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
