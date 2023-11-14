from pathlib import Path
import shutil
import subprocess
import sys
import os
PYGIT2_EXISTS = False
if not os.environ.get("INSTALL_VCPKG_USE_CLI_GIT"):
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

def fetch(self:pygit2.Remote, refspecs=None, message=None, callbacks=None, prune=0, proxy=None, depth=0):
    """Perform a fetch against this remote. Returns a <TransferProgress>
    object.
    Modified version of the pygit2 fetch function that allows for shallow clones

    Parameters:

    prune : enum
        Either <GIT_FETCH_PRUNE_UNSPECIFIED>, <GIT_FETCH_PRUNE>, or
        <GIT_FETCH_NO_PRUNE>. The first uses the configuration from the
        repo, the second will remove any remote branch in the local
        repository that does not exist in the remote and the last will
        always keep the remote branches

    proxy : None or True or str
        Proxy configuration. Can be one of:

        * `None` (the default) to disable proxy usage
        * `True` to enable automatic proxy detection
        * an url to a proxy (`http://proxy.example.org:3128/`)
        
    depth : int
        Depth to clone.

        If greater than zero, the clone will be a shallow clone.
        Defaults to 0 (unshallow).
    """
    from pygit2 import git_fetch_options
    from pygit2.ffi import C
    from pygit2.utils import to_bytes, StrArray
    from pygit2.remote import TransferProgress
    
    with git_fetch_options(callbacks) as payload:
        opts = payload.fetch_options
        opts.prune = prune
        opts.depth = depth
        # self.__set_proxy(opts.proxy_opts, proxy) -- not implemented
        with StrArray(refspecs) as arr:
            err = C.git_remote_fetch(self._remote, arr, opts, to_bytes(message))
            payload.check_error(err)

    return TransferProgress(C.git_remote_stats(self._remote))



def git_init(target: Path, url: str):
    if PYGIT2_EXISTS:
        repo = pygit2.init_repository(str(target), bare=False)
        repo.remotes.create("origin", url)
    else:
        subprocess.run(["git", "init"], cwd=target, check=True)
        subprocess.run(["git", "remote", "add", "origin", url], cwd=target, check=True)

def git_pull(target: Path, baseline_commit: str = None):
    if PYGIT2_EXISTS:
        print("USING PYGIT2")
        repo = pygit2.Repository(str(target))
        if (repo.is_bare or len(repo.remotes) == 0 or repo.remotes["origin"] is None):
            # just re-init it after removing the dir
            raise Exception("git repo not found, please remove the vcpkg directory and try again")
        refspecs = [baseline_commit] if baseline_commit else None
        fetch(repo.remotes["origin"], refspecs = refspecs, depth=1)
        fetch_head_ref = repo.lookup_reference("FETCH_HEAD")
        repo.checkout(fetch_head_ref)
    else:
        subprocess.run(["git", "fetch", "--depth=1", "origin", baseline_commit], cwd=target, check=True)
        subprocess.run(["git", "checkout", baseline_commit], cwd=target, check=True)

def git_clone(target: Path, url: str, baseline_commit: str = None):
    if baseline_commit:
        git_init(target, url)
        git_pull(target, baseline_commit)
    else:
        if PYGIT2_EXISTS:
                clone_repository(url, str(target), depth=1)
        else:
            subprocess.run(["git", "clone", "--depth=1", url, "vcpkg"], cwd=target, check=True)


def check_git_cli():
    try:
        subprocess.run(["git", "--version"], check=True)
    except subprocess.CalledProcessError:
        return False
    return True

def check_git() -> bool:
    if PYGIT2_EXISTS:
        return True
    return check_git_cli()

def get_baseline_from_vcpkgjson(vcpkg_json_path: Path) -> str:
    import json
    builtin_baseline = ""
    with open(vcpkg_json_path) as f:
        vcpkg_json = json.load(f)
        builtin_baseline = vcpkg_json["builtin-baseline"]
    return builtin_baseline

def install_vcpkg(build_temp: Path, baseline_commit: str):
    try:
        os.environ["VCPKG_DISABLE_METRICS"] = "true"
        print("VCPKG_ROOT not set, attempting to install vcpkg")
        vcpkg_root = build_temp / "vcpkg"
        vcpkg_exists = False
        if not check_git():
            raise Exception("git not found, please install git and try again")
        if (vcpkg_root.exists()):
            print("vcpkg already exists, attempting to update")
            # try git pull first; check if it fails
            try:
                git_pull(vcpkg_root, baseline_commit)
                vcpkg_exists = True
            except subprocess.CalledProcessError:
                print("Failed to update vcpkg, removing and re-cloning")
                shutil.rmtree(vcpkg_root)
        if not vcpkg_exists:
            # clone vcpkg
            git_clone(vcpkg_root, "https://github.com/microsoft/vcpkg.git", baseline_commit)
        if sys.platform.startswith("win32"):
            subprocess.run(["bootstrap-vcpkg.bat"], cwd=vcpkg_root, check=True)
        else:
            subprocess.run(["./bootstrap-vcpkg.sh"], cwd=vcpkg_root, check=True)
        # Set vcpkg root
        os.environ["VCPKG_ROOT"] = str(vcpkg_root)
    except subprocess.CalledProcessError:
        raise Exception("Failed to detect and install vcpkg, please install vcpkg and set VCPKG_ROOT to the vcpkg root directory")

