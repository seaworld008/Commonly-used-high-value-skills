"""Run LibreOffice only when the host permits its required local sockets.

No compatibility shim is compiled or injected. A failed permission check means
rendering has not run; callers must report it as blocked/unverified.
"""

import os
import socket
import subprocess


def get_soffice_env() -> dict:
    """Return the headless environment, failing if local sockets are blocked."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM):
            pass
    except OSError as exc:
        raise RuntimeError(
            "LibreOffice cannot use the host's required local sockets; "
            "rendering/recalculation has not run. No sandbox workaround was attempted."
        ) from exc

    env = os.environ.copy()
    env["SAL_USE_VCLPLUGIN"] = "svp"
    return env


def run_soffice(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["soffice"] + args, env=get_soffice_env(), **kwargs)


if __name__ == "__main__":
    import sys

    try:
        result = run_soffice(sys.argv[1:])
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    sys.exit(result.returncode)
