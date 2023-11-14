vcpkg_minimum_required(VERSION 2022-10-12) # for ${VERSION}

vcpkg_download_distfile(ARCHIVE
    URLS "https://github.com/llvm/llvm-project/releases/download/llvmorg-${VERSION}/openmp-${VERSION}.src.tar.xz"
    FILENAME "openmp-${VERSION}.tar.xz"
    SHA512 9c73bd5f6e09a2132afa2e3152d7506517bbd7fbf4294b30574bf42111f088ad8a32ff70c893d6e3211ceda735534b08cd60b3334f08150af8ba6b1ee61321b5
)

vcpkg_extract_source_archive(
    SOURCE_PATH
    ARCHIVE ${ARCHIVE}
)

vcpkg_download_distfile(CMAKE_ARCHIVE
    URLS "https://github.com/llvm/llvm-project/releases/download/llvmorg-${VERSION}/cmake-${VERSION}.src.tar.xz"
    FILENAME "cmake-${VERSION}.tar.xz"
    SHA512 bddfa97e6d1866a571d036490321099593063be33c38be1c6d117ea26d311876526d13760dc63155d3a7ea460f9c3de6da9911bdebeb286964ccdab377085a28
)
vcpkg_extract_source_archive(
    LLVM_CMAKE_FILES_SOURCE_PATH
    ARCHIVE ${CMAKE_ARCHIVE}
)

# copy cmake files from LLVM_CMAKE_FILES_SOURCE_PATH to the build path/cmake
# remove the current ${CURRENT_BUILDTREES_DIR}/cmake/ if it exists
set(LLVM_CMAKE_FILES_DEST "${CURRENT_BUILDTREES_DIR}/src/cmake/")
file(REMOVE_RECURSE "${LLVM_CMAKE_FILES_DEST}")
file(RENAME "${LLVM_CMAKE_FILES_SOURCE_PATH}" "${LLVM_CMAKE_FILES_DEST}")

set (LIBOMP_ENABLE_SHARED ON)
if (VCPKG_LIBRARY_LINKAGE MATCHES "static")
    set (LIBOMP_ENABLE_SHARED OFF)
endif()

set(OPENMP_ENABLE_LIBOMPTARGET OFF)
vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}"
    DISABLE_PARALLEL_CONFIGURE
    OPTIONS
        -DLIBOMP_ENABLE_SHARED=${LIBOMP_ENABLE_SHARED}
        -DLIBOMP_INSTALL_ALIASES=OFF
        -DOPENMP_ENABLE_LIBOMPTARGET=${OPENMP_ENABLE_LIBOMPTARGET}
        
)

vcpkg_cmake_install()
vcpkg_copy_pdbs()
vcpkg_fixup_pkgconfig()

if(VCPKG_TARGET_IS_WINDOWS AND NOT VCPKG_TARGET_IS_MINGW)
    file(GLOB_RECURSE pc_files "${CURRENT_PACKAGES_DIR}/*.pc")
    foreach(pc_file IN LISTS pc_files)
        vcpkg_replace_string("${pc_file}" " -lm" "")
    endforeach()
endif()



file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")

vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE.txt")
