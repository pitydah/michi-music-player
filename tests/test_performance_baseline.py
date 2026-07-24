"""Performance baseline tests — startup time, RAM, threads."""
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


class TestPerformance:
    def test_startup_time(self):
        """Full bootstrap should complete quickly."""
        import time
        start = time.time()
        # Import and build services (no GUI)
        from core.service_container import ServiceContainer
        from core.composition.infrastructure import build
        c = ServiceContainer()
        build(c)
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Startup too slow: {elapsed:.2f}s"

    def test_qml_only_gate(self):
        """QML-only gate should pass without violations."""
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "qml_only_gate.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"Gate failed: {result.stderr}"
