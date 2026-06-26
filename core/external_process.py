"""External process runner — safe subprocess execution with timeout + cancel."""

import logging
import subprocess

logger = logging.getLogger("michi.process_runner")


class ProcessResult:
    def __init__(self):
        self.ok: bool = False
        self.returncode: int = -1
        self.stdout: str = ""
        self.stderr: str = ""
        self.timed_out: bool = False
        self.cancelled: bool = False
        self.error: str = ""


def run_process(
    args: list[str],
    timeout: float = 30.0,
    max_stdout_bytes: int = 1024 * 1024,
    max_stderr_bytes: int = 256 * 1024,
    cancel_token: dict | None = None,
    text: bool = True,
) -> ProcessResult:
    """Run an external process safely.

    Args:
        args: Command and arguments (no shell parsing).
        timeout: Seconds before SIGKILL.
        max_stdout_bytes/max_stderr_bytes: Truncate output at these limits.
        cancel_token: If dict with key 'cancelled' is set to True, kill the process.
        text: Decode output as UTF-8.

    Returns ProcessResult with ok, returncode, stdout, stderr, timed_out, cancelled, error.
    """
    result = ProcessResult()

    if not args:
        result.error = "No command provided"
        return result

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
        )

        cancelled = False
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            result.timed_out = True
        except Exception:
            proc.kill()
            stdout, stderr = "", ""

        # Check cancel token
        if cancel_token and cancel_token.get("cancelled"):
            proc.kill()
            cancelled = True

        result.returncode = proc.returncode
        result.stdout = (stdout or "")[:max_stdout_bytes]
        result.stderr = (stderr or "")[:max_stderr_bytes]
        result.cancelled = cancelled
        result.ok = proc.returncode == 0 and not cancelled and not result.timed_out
    except FileNotFoundError:
        result.error = f"Command not found: {args[0]}"
    except OSError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Process error: {e}"

    return result
