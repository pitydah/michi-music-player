"""M11.3D — real MPD runtime smoke (private instance only).

SKIP truthful solo si el ejecutable mpd está genuinamente ausente; con el
ejecutable presente, los fallos de arranque/config/socket son FAIL."""

import os
import shutil

import pytest

pytestmark = pytest.mark.mpd_runtime

REQUIRED = [
    "mpd",
]


def _require_mpd():
    if shutil.which("mpd") is None:
        pytest.skip("dependency absent: mpd executable not found in PATH")
    return True


def test_real_private_runtime_smoke(qapp, tmp_path):
    """Arranca UNA instancia MPD privada (runtime + socket propios),
    handshake, status, addid/clear, y teardown completo."""
    _require_mpd()

    from michi.infrastructure.audio_engines.mpd import (
        _ManagedMpdRuntime,
        _MpdProtocolClient,
    )

    runtime = _ManagedMpdRuntime(startup_timeout=10.0)
    runtime.start()
    try:
        assert runtime.socket_path is not None
        assert os.path.exists(runtime.socket_path)
        assert runtime.child_alive()
        # handshake + status reales
        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        status = client.status()
        assert "state" in status
        # addid/clear sobre un archivo inexistente → ACK determinista o error
        # (no exigimos reproducción; solo que el protocolo responda)
        try:
            client.clear()
            client.addid(str(tmp_path / "nope.flac"))
        except Exception as exc:  # noqa: BLE001 — runtime truth
            # un ACK o error del daemon es una respuesta VÁLIDA del
            # protocolo; un EOF/socket roto sería un fallo real
            assert "EOF" not in str(exc), f"protocol broken: {exc}"
        client.close()
    finally:
        runtime.close()
    # teardown completo: sin proceso, sin socket, sin runtime
    assert runtime.process is None or runtime.process.poll() is not None
    assert runtime.socket_path is None
    assert runtime.runtime_dir is None
