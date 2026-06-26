"""ShutdownManager — ordered shutdown of app services on close."""
import logging


class ShutdownManager:
    """Registers stop callbacks and executes them in reverse order on shutdown."""

    def __init__(self):
        self._items: list[tuple[str, callable]] = []

    def register(self, name: str, stop_fn):
        """Register a named stop function. Called in reverse order."""
        self._items.append((name, stop_fn))

    def shutdown(self):
        """Execute all registered stop functions. Errors are logged, not re-raised."""
        log = logging.getLogger("michi.shutdown")
        for name, fn in reversed(self._items):
            try:
                fn()
            except Exception as e:
                log.warning("Error stopping %s: %s", name, e)
