"""Test Evidence V7 plugin — conftest.py extracts qml_module/qml_dimension markers."""
import pytest


@pytest.mark.qml_module("test_mod")
@pytest.mark.qml_dimension("primary_action")
def test_with_markers():
    assert True


@pytest.mark.qml_module("test_mod")
def test_module_only():
    assert True


@pytest.mark.qml_dimension("read")
def test_dimension_only():
    assert True


def test_no_markers():
    assert True


class TestWithClassMarker:
    pytestmark = [pytest.mark.qml_module("class_mod"), pytest.mark.qml_dimension("integration")]

    def test_class_marked(self):
        assert True

    def test_class_marked_too(self):
        assert True


@pytest.mark.qml_module("multi")
@pytest.mark.qml_dimension("write")
@pytest.mark.qml_dimension("persistence")
def test_multi_dimension():
    assert True
