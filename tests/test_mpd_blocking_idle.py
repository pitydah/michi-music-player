"""GATE A1 (M11.3D-R3): terminación determinista de un recv() REAL
bloqueado en el socket idle AF_UNIX."""

import socket
import threading

from michi.infrastructure.audio_engines.mpd import _MpdProtocolClient


def test_real_blocked_idle_recv_unblocked_by_close(tmp_path):
    """Server real AF_UNIX: greeting + recibe 'idle player' y NO responde.
    El worker queda bloqueado en recv(); client.close() debe despertarlo."""
    sock_path = str(tmp_path / "idle.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    server_confirmed = threading.Event()
    server_errors = []

    def server_main():
        try:
            conn, _ = server.accept()
            with conn:
                conn.sendall(b"OK MPD 0.23.5\n")
                data = conn.recv(4096)
                assert b"idle player" in data
                server_confirmed.set()
                # NO respondemos: el cliente queda bloqueado en recv()
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return  # el cliente cerró
        except Exception as exc:  # noqa: BLE001
            server_errors.append(exc)
        finally:
            server.close()

    server_thread = threading.Thread(target=server_main, daemon=True)
    server_thread.start()

    client = _MpdProtocolClient(sock_path, timeout=None)
    client.connect()
    worker_errors = []
    worker_done = threading.Event()

    def worker():
        try:
            client.idle("player")
        except BaseException as exc:  # noqa: BLE001 — propagación explícita
            worker_errors.append(exc)
        finally:
            worker_done.set()

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    assert server_confirmed.wait(timeout=3.0), "server no recibió idle"
    assert worker_done.wait(timeout=0.5) is False  # worker BLOQUEADO

    # cancelación: close() debe despertar el recv bloqueado
    client.close()
    assert worker_done.wait(timeout=3.0), "worker siguió bloqueado tras close()"
    worker_thread.join(timeout=2.0)
    assert not worker_thread.is_alive()
    assert server_errors == []
    worker_thread.join()
    server_thread.join(timeout=2.0)
