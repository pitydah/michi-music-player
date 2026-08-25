"""Entry point: python -m michi"""

import sys

from michi.bootstrap import ApplicationContainer


def _shutdown_best_effort(container: ApplicationContainer) -> None:
    """Guaranteed-lifecycle shutdown on the ERROR path (AR-04).

    The PRIMARY exception always wins (first-error-wins): if shutdown also
    fails while we are already unwinding an error, the shutdown failure is
    logged as a SECONDARY diagnostic and must never mask the primary."""
    try:
        container.shutdown()
    except Exception as exc:  # noqa: BLE001 — shutdown is best-effort here
        print(
            f"WARNING: shutdown failed while handling an error: {exc}", file=sys.stderr
        )


def main() -> int:
    container = ApplicationContainer()
    try:
        container.initialize()
    except BaseException:
        # initialize() failed → shutdown the partial container safely, then
        # re-raise the original failure (never masked by teardown errors).
        _shutdown_best_effort(container)
        raise
    try:
        exit_code = container.run()
    except BaseException:
        # run() failed → same guaranteed shutdown, primary preserved.
        _shutdown_best_effort(container)
        raise
    # Normal GUI exit: shutdown errors are FATAL here (never swallowed).
    container.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
