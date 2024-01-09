import subprocess
from pathlib import Path

import pygit2

PYGIT2_EXISTS = True


def git_clone(target: Path, url: str):
    if PYGIT2_EXISTS:
        print("USING PYGIT2")
        callbacks = pygit2.RemoteCallbacks()
        callbacks.repository = None
        callbacks.remote = None
        with pygit2.git_clone_options(callbacks):
            callbacks.clone_options.fetch_opts.depth = 1
            pygit2.clone_repository(url, str(target), callbacks=callbacks)
    else:
        print("USING COMMAND LINE!!!")
        subprocess.run(
            ["git", "clone", "--depth=1", url, "vcpkg"], cwd=target, check=True
        )


git_clone(Path("vcpkg"), "https://github.com/microsoft/vcpkg.git")
