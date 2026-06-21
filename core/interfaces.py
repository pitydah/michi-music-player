"""Interfaces — abstract definitions for controller contracts."""

from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget


class IPlaybackController(ABC):
    @abstractmethod
    def play(self, filepath: str, title: str = "", artist: str = ""):
        ...

    @abstractmethod
    def play_url(self, url: str, title: str = "", artist: str = ""):
        ...

    @abstractmethod
    def toggle(self):
        ...

    @abstractmethod
    def stop(self):
        ...

    @abstractmethod
    def seek(self, seconds: float):
        ...

    @abstractmethod
    def set_volume(self, vol: int):
        ...

    @abstractmethod
    def play_next(self):
        ...

    @abstractmethod
    def play_prev(self):
        ...

    @abstractmethod
    def enqueue(self, paths: list, play_now: bool = True):
        ...

    @abstractmethod
    def clear_queue(self):
        ...

    @abstractmethod
    def get_queue(self) -> list[dict]:
        ...

    @abstractmethod
    def reorder_queue(self, filepaths: list[str]):
        ...

    @abstractmethod
    def toggle_shuffle(self):
        ...

    @abstractmethod
    def toggle_repeat(self) -> str:
        ...

    @abstractmethod
    def set_output_device(self, device):
        ...

    @property
    @abstractmethod
    def state(self):
        ...

    @property
    @abstractmethod
    def current(self) -> str:
        ...


class IViewController(ABC):
    @abstractmethod
    def register(self, name: str, widget: QWidget):
        ...

    @abstractmethod
    def replace(self, name: str, widget: QWidget, delete_old: bool = True):
        ...

    @abstractmethod
    def show(self, name: str):
        ...

    @abstractmethod
    def current(self) -> str:
        ...

    @abstractmethod
    def widget(self, name: str) -> QWidget | None:
        ...

