"""Cancel only a conversion process started for this workspace."""
import os
import signal
import subprocess
import time


class ConversionCancelled(Exception):
    pass


def check_cancelled(cancel):
    if cancel is not None and cancel.is_set():
        raise ConversionCancelled()


def run_converter(args, *, timeout, cancel=None):
    check_cancelled(cancel)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if cancel is None:
        return subprocess.run(args, capture_output=True, timeout=timeout, creationflags=flags)
    if os.name == "nt":
        from .windows_converter import run_windows_converter
        return run_windows_converter(args, timeout, cancel)
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags,
                               start_new_session=os.name != "nt")
    deadline = time.monotonic() + timeout
    try:
        while True:
            check_cancelled(cancel)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = process.communicate(timeout=min(.15, remaining))
                check_cancelled(cancel)
                return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    raise
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            if process.poll() is None:
                process.kill()
        process.communicate()
