"""Test that the wheel builds and contains all required packages."""
import glob
import zipfile


def test_wheel_builds():
    """Wheel can be built."""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"Build failed: {result.stderr[-500:]}"


def test_wheel_contains_all_packages():
    """Wheel contains all required packages."""
    whl = sorted(glob.glob('dist/*.whl'))
    assert len(whl) > 0, "No wheel found"

    with zipfile.ZipFile(whl[-1]) as z:
        names = z.namelist()
        required = ['michi/', 'audio/', 'core/', 'library/', 'ui_qml/', 'ui_qml_bridge/']
        for pkg in required:
            assert any(n.startswith(pkg) for n in names), f"Missing: {pkg}"
        assert any(n.endswith('.qml') for n in names), "Missing QML files"
        assert any(n.endswith('qmldir') for n in names), "Missing qmldir"


def test_wheel_size():
    """Wheel is not unreasonably large."""
    whl = sorted(glob.glob('dist/*.whl'))
    size = whl[-1].stat().st_size
    assert size < 50_000_000, f"Wheel too large: {size / 1e6:.1f}MB"
    assert size > 100_000, f"Wheel suspiciously small: {size / 1e3:.1f}KB"
