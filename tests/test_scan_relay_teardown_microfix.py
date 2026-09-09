"""POST-R4 MICROFIX — relay teardown exact-slot (KCR-010).

El baseline (184f711) hacía ``signal.disconnect()`` global en el
teardown: con la topología del artwork runner (done conectado, progress
SIN conectar), PySide6 emitía el RuntimeWarning "Failed to disconnect
(None) from signal progress". La corrección registra las conexiones en
``connect_relay`` y el teardown desconecta SOLO los slots conocidos —
la operación inválida no existe.

RED (reproducido contra 184f711):
    RuntimeWarnings: 1
      libpyside: Failed to disconnect (None) from signal progress
"""

import warnings
from pathlib import Path

from PySide6.QtCore import QObject, Slot

from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner


class _SlotOwner(QObject):
    """Slots reales (QObject bound methods: el tipo que conecta el
    composition root productivo)."""

    def __init__(self):
        super().__init__()
        self.done_calls = []
        self.progress_calls = []

    @Slot(int, object, object)
    def on_done(self, generation, result, error):
        self.done_calls.append(generation)

    @Slot(int, object)
    def on_progress(self, generation, progress):
        self.progress_calls.append(generation)


def _run_teardown(runner):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        runner.disconnect_relay()
    return [
        w
        for w in caught
        if issubclass(w.category, RuntimeWarning)
        or issubclass(w.category, RuntimeError)
        or issubclass(w.category, TypeError)
    ]


class TestArtworkTopology:
    """Caso A: done conectado, progress SIN conectar (artwork runner)."""

    def test_teardown_with_unconnected_progress_emits_no_warning(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.done, owner.on_done)  # progress NO

        caught = _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"

    def test_only_registered_done_is_disconnected(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.done, owner.on_done)
        runner.disconnect_relay()
        # el slot registrado ya no recibe emisiones
        relay.done.emit(1, None, None)
        relay.progress.emit(1, None)
        assert owner.done_calls == []
        assert owner.progress_calls == []


class TestFullScanTopology:
    """Caso B: done + progress conectados (library/source runners)."""

    def test_teardown_disconnects_both_and_emits_no_warning(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.done, owner.on_done)
        runner.connect_relay(relay.progress, owner.on_progress)

        caught = _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"
        relay.done.emit(1, None, None)
        relay.progress.emit(1, None)
        assert owner.done_calls == [], "el slot done sigue conectado"
        assert owner.progress_calls == [], "el slot progress sigue conectado"


class TestIdempotence:
    """Caso C: dos llamadas consecutivas = no-op limpio."""

    def test_double_teardown_is_clean(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.done, owner.on_done)
        runner.connect_relay(relay.progress, owner.on_progress)

        caught = _run_teardown(runner) + _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"


class TestPartialTopology:
    """Caso D: solo progress registrado (sin done)."""

    def test_progress_only_registration(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.progress, owner.on_progress)  # done NO

        caught = _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"
        relay.progress.emit(1, None)
        relay.done.emit(1, None, None)
        assert owner.progress_calls == []
        assert owner.done_calls == []


class TestExternallyDisconnectedSlot:
    """Killcritic #6 (límite documentado de la API): si un slot se retira
    EXTERNAMENTE antes del teardown, el disconnect(slot) exacto de
    PySide6 emite el RuntimeWarning de libpyside — no hay API estable
    para preguntar si una conexión específica sigue viva (el
    SignalInstance NO expone receivers(): AttributeError demostrado) y
    la captura de warnings está fuera del contrato de este microfix.

    En el flujo productivo el caso no ocurre: disconnect_relay() es la
    ÚNICA autoridad de retiro de los relays y el teardown del container
    preserva a los owners de los slots hasta después de la desconexión
    (los casos A-D, que cubren la topología real, emiten 0 warnings)."""

    def test_productivo_slots_are_alive_until_teardown(self):
        """Los owners productivos se desconectan SOLO por el runner: el
        registro y el teardown agotan exactamente las conexiones."""
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        owner = _SlotOwner()
        runner.connect_relay(relay.done, owner.on_done)
        runner.connect_relay(relay.progress, owner.on_progress)
        # el flujo productivo: nadie retira antes; el teardown retira todo.
        caught = _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"
        assert runner._relay_connections == [], "registro agotado"


class TestNothingRegistered:
    """Killcritic: sin conexiones registradas, el teardown es no-op."""

    def test_teardown_with_no_registrations(self):
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        caught = _run_teardown(runner)
        assert caught == [], f"warnings/excepciones inesperadas: {caught}"


class TestProductiveTopologySeal:
    """POST-R4 microfix (§9): el composition root registra las topologías
    EXACTAS por runner — library/source: done+progress; artwork: done
    únicamente. Este seal falla si alguien vuelve a asumir que todos los
    ThreadScanRunner conectan ambas señales (la regresión exacta del
    RuntimeWarning)."""

    BOOTSTRAP = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "michi"
        / "bootstrap"
        / "__init__.py"
    ).read_text(encoding="utf-8")

    def test_artwork_runner_registers_done_only(self):
        artwork_segment = self.BOOTSTRAP.split("artwork_runner.connect_relay(", 1)[1]
        artwork_segment = artwork_segment.split("source_scan_runner.connect_relay(", 1)[
            0
        ]
        assert "artwork_relay.done" in artwork_segment
        assert "artwork_relay.progress" not in artwork_segment, (
            "el artwork runner registra SOLO done (progress no existe): "
            "asumir ambas señales reproduce el RuntimeWarning"
        )

    def test_library_and_source_runners_register_both(self):
        # el prefijo con indentación distingue scan_runner del substring
        # dentro de source_scan_runner.
        assert self.BOOTSTRAP.count("\n    scan_runner.connect_relay(") == 2
        assert self.BOOTSTRAP.count("\n    source_scan_runner.connect_relay(") == 2
        assert "scan_relay.progress" in self.BOOTSTRAP
        assert "source_scan_relay.progress" in self.BOOTSTRAP

    def test_real_container_teardown_emits_no_disconnect_warning(self, tmp_path):
        """El container real (initialize + shutdown) ejecuta el teardown
        de los 3 runners: la topología artwork (progress sin conectar) ya
        no produce el RuntimeWarning de libpyside."""
        import os
        import sys

        os.environ["XDG_DATA_HOME"] = str(tmp_path / "data")
        os.environ["XDG_CACHE_HOME"] = str(tmp_path / "cache")
        os.environ["XDG_CONFIG_HOME"] = str(tmp_path / "config")
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication(sys.argv)
        from michi.bootstrap import ApplicationContainer

        container = ApplicationContainer()
        container.initialize()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            container.shutdown()
        relay_warnings = [
            w
            for w in caught
            if issubclass(w.category, RuntimeWarning)
            and "Failed to disconnect" in str(w.message)
        ]
        assert relay_warnings == [], (
            f"el teardown del container emite {len(relay_warnings)} "
            f"RuntimeWarning(s) de desconexión: {relay_warnings[:1]}"
        )
