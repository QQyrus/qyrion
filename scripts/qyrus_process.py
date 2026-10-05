"""Launch plugin commands without the Windows CRT exec environment path."""

from __future__ import annotations

import os
import shutil
import subprocess


_WINDOWS = os.name == "nt"


def launch_command(command: list[str], environment: dict[str, str]) -> int:
    """Run with inherited stdio and credentials only in the child environment.

    Windows exec*e can crash inside the CRT when building the environment
    block (CPython issue 143327). Use subprocess/CreateProcess there and wait
    for completion; POSIX keeps process replacement for stream/signal parity.
    Resolve Windows executables explicitly so PATH/PATHEXT and spaces work.
    Do not capture protocol output, invoke a shell, or retry a command.

    Example:
        return launch_command(["qyrion", "sessions", "list", "--json"], env)
    """
    if not _WINDOWS:
        os.execvpe(command[0], command, environment)
        return 0  # Successful POSIX exec never returns.

    executable = shutil.which(command[0], path=environment.get("PATH"))
    if executable is None:
        raise FileNotFoundError("Command executable is not installed or is unavailable.")
    try:
        result = subprocess.run(
            [executable, *command[1:]], env=environment, shell=False, check=False,
        )
    except KeyboardInterrupt:
        return 130
    # sys.exit accepts a signed C int on Windows; preserve all NTSTATUS bits.
    return result.returncode - 0x100000000 if result.returncode > 0x7FFFFFFF else result.returncode
