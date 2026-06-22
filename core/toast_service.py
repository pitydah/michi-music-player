"""Toast service — unified toast notification API for Michi Music Player."""
from ui.toast_notification import ToastNotification


class ToastService:
    """Wraps ToastNotification classmethods into a simple service interface."""

    def __init__(self, parent=None):
        self._parent = parent

    def set_parent(self, parent):
        self._parent = parent

    def show(self, text: str, level: str = "info", duration: int = None):
        """Show a toast notification. Level: info, success, warning, error."""
        if level == "success":
            return ToastNotification.success(text, self._parent, duration or 3000)
        elif level == "warning":
            return ToastNotification.warning(text, self._parent, duration or 5000)
        elif level == "error":
            return ToastNotification.error(text, self._parent, duration or 6000)
        else:
            return ToastNotification.info(text, self._parent, duration or 4000)

    def info(self, text: str):
        return self.show(text, "info")

    def success(self, text: str):
        return self.show(text, "success")

    def warning(self, text: str):
        return self.show(text, "warning")

    def error(self, text: str):
        return self.show(text, "error")
