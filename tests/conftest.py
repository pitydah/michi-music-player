"""Root conftest: ensures core package is fully loaded before any test."""
import core  # noqa: F401 — ensures core/__init__.py runs first
