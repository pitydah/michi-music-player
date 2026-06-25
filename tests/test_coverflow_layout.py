"""Tests for coverflow_layout() — position, rotation, scale, symmetry."""
import pytest

from library.coverflow import coverflow_layout

VW, VH = 1024, 600
CW, CH = 260, 260


def test_center_exact():
    state = coverflow_layout(0.0, VW, VH, CW, CH)
    assert state["x"] == pytest.approx(VW / 2, abs=1.0)
    assert state["y"] == pytest.approx(VH / 2 - 20, abs=1.0)
    assert state["scale"] == pytest.approx(1.0, abs=0.01)
    assert state["rot"] == 0.0
    assert state["visible"] is True


def test_offset_plus_one():
    state = coverflow_layout(1.0, VW, VH, CW, CH)
    assert state["x"] > VW / 2 + 150
    assert state["x"] < VW / 2 + 220
    assert state["scale"] == pytest.approx(0.88, abs=0.02)
    assert state["rot"] == pytest.approx(22.0, abs=1.0)


def test_offset_minus_one():
    state = coverflow_layout(-1.0, VW, VH, CW, CH)
    assert state["x"] < VW / 2 - 150
    assert state["x"] > VW / 2 - 220
    assert state["scale"] == pytest.approx(0.88, abs=0.02)
    assert state["rot"] == pytest.approx(-22.0, abs=1.0)


def test_symmetry():
    for offset in [0.5, 1.0, 2.0, 3.5]:
        pos = coverflow_layout(offset, VW, VH, CW, CH)
        neg = coverflow_layout(-offset, VW, VH, CW, CH)
        assert pos["scale"] == pytest.approx(neg["scale"])
        assert pos["z"] == pytest.approx(neg["z"])
        assert pos["rot"] == pytest.approx(-neg["rot"])
        center = VW / 2
        assert (center - neg["x"]) == pytest.approx(pos["x"] - center, abs=2.0)


def test_far_offset_scale():
    state = coverflow_layout(5.0, VW, VH, CW, CH)
    assert state["scale"] >= 0.45
    assert state["visible"] is True


def test_dead_zone():
    state = coverflow_layout(0.1, VW, VH, CW, CH)
    assert state["rot"] == 0.0
