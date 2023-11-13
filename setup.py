import os
import re
import subprocess
import sys
from pathlib import Path
import shutil

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.dist import Distribution
from pybind11 import get_cmake_dir
import pybind11_stubgen
import importlib



PYGIT2_EXISTS = False
try:
    import pygit2
    PYGIT2_EXISTS = True
except ImportError:
    PYGIT2_EXISTS = False
    pass


def clone_repository(
        url, path, bare=False, repository=None, remote=None,
        checkout_branch=None, callbacks=None, depth=0):
    """
    Clones a new Git repository from *url* in the given *path*.
    Modded version of the pygit2 clone_repository function that allows for shallow clones
    
    Returns: a Repository class pointing to the newly cloned repository.

    Parameters:

    url : str
        URL of the repository to clone.
    path : str
        Local path to clone into.
    bare : bool
        Whether the local repository should be bare.
    remote : callable
        Callback for the remote to use.

        The remote callback has `(Repository, name, url) -> Remote` as a
        signature. The Remote it returns will be used instead of the default
        one.
    repository : callable
        Callback for the repository to use.

        The repository callback has `(path, bare) -> Repository` as a
        signature. The Repository it returns will be used instead of creating a
        new one.
    checkout_branch : str
        Branch to checkout after the clone. The default is to use the remote's
        default branch.
    callbacks : RemoteCallbacks
        Object which implements the callbacks as methods.

        The callbacks should be an object which inherits from
        `pyclass:RemoteCallbacks`.
    depth : int
        Depth to clone.

        If greater than zero, the clone will be a shallow clone.
        Defaults to 0 (unshallow).
    """
    if not PYGIT2_EXISTS:
        raise Exception("pygit2 not found, please install pygit2 and try again")
    from pygit2 import git_clone_options, git_fetch_options, RemoteCallbacks, Repository
    from pygit2.ffi import ffi, C
    from pygit2.utils import to_bytes


    if callbacks is None:
        callbacks = RemoteCallbacks()

    # Add repository and remote to the payload
    payload = callbacks
    payload.repository = repository
    payload.remote = remote

    with git_clone_options(payload):
        opts = payload.clone_options
        opts.bare = bare

        if checkout_branch:
            checkout_branch_ref = ffi.new('char []', to_bytes(checkout_branch))
            opts.checkout_branch = checkout_branch_ref

        with git_fetch_options(payload, opts=opts.fetch_opts):
            opts.fetch_opts.depth = depth
            crepo = ffi.new('git_repository **')
            err = C.git_clone(crepo, to_bytes(url), to_bytes(path), opts)
            payload.check_error(err)

    # Ok
    return Repository._from_c(crepo[0], owned=True)


# Convert distutils Windows platform specifiers to CMake -A arguments
PLAT_TO_CMAKE = {
    "win32": "Win32",
    "win-amd64": "x64",
    "win-arm32": "ARM",
    "win-arm64": "ARM64",
}


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    mapping = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)



# A CMakeExtension needs a sourcedir instead of a file list.
# The name must be the _single_ output extension from the CMake build.
# If you need multiple extensions, see scikit-build.
class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())


class CMakeBuild(build_ext):

    def build_extension(self, ext: CMakeExtension) -> None:
        # Must be in this form due to bug in .resolve() only fixed in Python 3.10+
        ext_fullpath = Path.cwd() / self.get_ext_fullpath(ext.name)
        extdir = ext_fullpath.parent.resolve()

        # Using this requires trailing slash for auto-detection & inclusion of
        # auxiliary "native" libs

        debug = int(os.environ.get("DEBUG", 0)) if self.debug is None else self.debug
        cfg = "Debug" if debug else "Release"

        # CMake lets you override the generator - we need to check this.
        # Can be set with Conda-Build, for example.
        cmake_generator = os.environ.get("CMAKE_GENERATOR", "")

        # Set Python_EXECUTABLE instead if you use PYBIND11_FINDPYTHON
        # EXAMPLE_VERSION_INFO shows you how to pass a value into the C++ code
        # from Python.
        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}{os.sep}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",  # not used on MSVC, but no harm
        ]
        build_args = []
        # Adding CMake arguments set as environment variable
        # (needed e.g. to build for ARM OSx on conda-forge)
        if "CMAKE_ARGS" in os.environ:
            cmake_args += [item for item in os.environ["CMAKE_ARGS"].split(" ") if item]

        # In this example, we pass in the version to C++. You might not need to.
        cmake_args += [f"-DEXAMPLE_VERSION_INFO={self.distribution.get_version()}"]

        if self.compiler.compiler_type != "msvc":
            # Using Ninja-build since it a) is available as a wheel and b)
            # multithreads automatically. MSVC would require all variables be
            # exported for Ninja to pick it up, which is a little tricky to do.
            # Users can override the generator with CMAKE_GENERATOR in CMake
            # 3.15+.
            if not cmake_generator or cmake_generator == "Ninja":
                try:
                    import ninja

                    ninja_executable_path = Path(ninja.BIN_DIR) / "ninja"
                    cmake_args += [
                        "-GNinja",
                        f"-DCMAKE_MAKE_PROGRAM:FILEPATH={ninja_executable_path}",
                    ]
                except ImportError:
                    pass

        else:
            # Single config generators are handled "normally"
            single_config = any(x in cmake_generator for x in {"NMake", "Ninja"})

            # CMake allows an arch-in-generator style for backward compatibility
            contains_arch = any(x in cmake_generator for x in {"ARM", "Win64"})

            # Specify the arch if using MSVC generator, but only if it doesn't
            # contain a backward-compatibility arch spec already in the
            # generator name.
            if not single_config and not contains_arch:
                cmake_args += ["-A", PLAT_TO_CMAKE[self.plat_name]]

            # Multi-config generators have a different way to specify configs
            if not single_config:
                cmake_args += [
                    f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{cfg.upper()}={extdir}"
                ]
                build_args += ["--config", cfg]

        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
            if archs:
                cmake_args += ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]

        # Set CMAKE_BUILD_PARALLEL_LEVEL to control the parallel build level
        # across all generators.
        if "CMAKE_BUILD_PARALLEL_LEVEL" not in os.environ:
            # self.parallel is a Python 3 only way to set parallel jobs by hand
            # using -j in the build_ext call, not supported by pip or PyPA-build.
            if hasattr(self, "parallel") and self.parallel:
                # CMake 3.12+ only.
                build_args += [f"-j{self.parallel}"]

        build_temp = Path(self.build_temp) / ext.name
        if not build_temp.exists():
            build_temp.mkdir(parents=True)
        if not os.environ.get("VCPKG_ROOT") and not os.environ.get("LIBDARKNETPY_NO_VCPKG"):
            self.install_vcpkg(build_temp)
        print("VCPKG_ROOT set to {}".format(os.environ.get("VCPKG_ROOT")))
        #include vcpkg toolchain file from VCPKG_ROOT
        if not os.environ.get("VCPKG_ROOT"):
            raise Exception("VCPKG_ROOT not set, please install vcpkg and set VCPKG_ROOT to the vcpkg root directory")
        if not os.environ.get("VCPKG_DEFAULT_TRIPLET"):
            if sys.platform.startswith("win32"):
                os.environ["VCPKG_DEFAULT_TRIPLET"] = "x64-windows-static-md"
            # We don't need to set it for linux and mac because they compile statically by default
        cmake_args += ["-DCMAKE_TOOLCHAIN_FILE={}".format(os.environ.get("VCPKG_ROOT") + "/scripts/buildsystems/vcpkg.cmake")]
        # set pybind11_DIR
        cmake_args += ["-Dpybind11_DIR={}".format(get_cmake_dir())]
        subprocess.run(
            ["cmake", ext.sourcedir, *cmake_args], cwd=build_temp, check=True
        )
        subprocess.run(
            ["cmake", "--build", ".", *build_args], cwd=build_temp, check=True
        )
        # This isn't working right now
        # self.generate_pyi(build_temp)

    def check_git_cli(self):
        try:
            subprocess.run(["git", "--version"], check=True)
        except subprocess.CalledProcessError:
            return False
        return True

    def check_git(self) -> bool:
        if PYGIT2_EXISTS:
            return True
        return self.check_git_cli()
        
    def git_pull(self, target: Path):
        if PYGIT2_EXISTS:
            print("USING PYGIT2")
            repo = pygit2.Repository(str(target))
            repo.remotes["origin"].fetch()
            repo.checkout(repo.head.name)
            repo.set_head(repo.head.name)
        else:
            print("USING COMMAND LINE!!!")
            subprocess.run(["git", "pull"], cwd=target, check=True)
 
    def git_clone(self, target: Path, url: str):
        if PYGIT2_EXISTS:
            print("USING PYGIT2")
            clone_repository(url, str(target), depth=1)
        else:
            print("USING COMMAND LINE!!!")
            subprocess.run(["git", "clone", "--depth=1", url, "vcpkg"], cwd=target, check=True)

    def install_vcpkg(self, build_temp: Path):
        try:
            os.environ["VCPKG_DISABLE_METRICS"] = "true"
            print("VCPKG_ROOT not set, attempting to install vcpkg")
            vcpkg_root = build_temp / "vcpkg"
            vcpkg_exists = False
            if not self.check_git():
                raise Exception("git not found, please install git and try again")
            if (vcpkg_root.exists()):
                print("vcpkg already exists, attempting to update")
                # try git pull first; check if it fails
                try:
                    self.git_pull(vcpkg_root)
                    vcpkg_exists = True
                except subprocess.CalledProcessError:
                    print("Failed to update vcpkg, removing and re-cloning")
                    shutil.rmtree(vcpkg_root)
            if not vcpkg_exists:
                # clone vcpkg
                self.git_clone(vcpkg_root, "https://github.com/microsoft/vcpkg.git")
            if sys.platform.startswith("win32"):
                subprocess.run(["bootstrap-vcpkg.bat"], cwd=vcpkg_root, check=True)
            else:
                subprocess.run(["./bootstrap-vcpkg.sh"], cwd=vcpkg_root, check=True)
            # Set vcpkg root
            os.environ["VCPKG_ROOT"] = str(vcpkg_root)
        except subprocess.CalledProcessError:
            raise Exception("Failed to detect and install vcpkg, please install vcpkg and set VCPKG_ROOT to the vcpkg root directory")

        
    def generate_pyi(self, build_temp) -> None:
        # Configure custom loader
        _PackageFinder.mapping = {"libdarknetpy": str(build_temp / "libdarknetpy")}
        sys.meta_path.insert(0, _PackageFinder)

        # Generate pyi modules
        stubgen_args = [
            "--root-suffix=''",
            "--ignore-all-errors",
            "libdarknetpy",
        ]
        # subprocess.run(
        #     ["pybind11-stubgen"] + stubgen_args, cwd=build_temp, check=True
        # )
        args = pybind11_stubgen.arg_parser().parse_args(stubgen_args)

        parser = pybind11_stubgen.stub_parser_from_args(args)
        printer = pybind11_stubgen.Printer(invalid_expr_as_ellipses=not args.print_invalid_expressions_as_is)

        out_dir, sub_dir = pybind11_stubgen.to_output_and_subdir(
            output_dir=args.output_dir,
            module_name=args.module_name,
            root_suffix=args.root_suffix,
        )

        pybind11_stubgen.run(
            parser,
            printer,
            args.module_name,
            out_dir,
            sub_dir=sub_dir,
            dry_run=args.dry_run,
            writer=pybind11_stubgen.Writer(stub_ext=args.stub_extension),
        )


class LibdarknetpyDistribution(Distribution):
    def has_ext_modules(self):
        return True

# The information here can also be placed in setup.cfg - better separation of
# logic and declaration, and simpler if you include description/version in a file.
setup(
    name="libdarknetpy",
    version="0.0.1",
    author="NikitaLita",
    author_email="nikitalita@fakeemail.com",
    description="A test project using pybind11 and CMake",
    long_description="",
    packages=["libdarknetpy"],
    package_data={"libdarknetpy": ["py.typed", "*.so", "*.pyi"]},
    package_dir={"libdarknetpy": "src/libdarknetpy"},
    ext_modules=[CMakeExtension("libdarknetpy._libdarknetpy")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
    extras_require={"test": ["pytest>=6.0"]},
    python_requires=">=3.7",
    distclass=LibdarknetpyDistribution,
    requires=["pybind11"]
)
