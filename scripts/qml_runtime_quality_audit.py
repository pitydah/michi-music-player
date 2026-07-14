#!/usr/bin/env python3
"""Runtime Quality Audit — measures leaked objects, threads, timers, memory, DB,
external processes, navigation cycles, stale callbacks, duplicate context properties.

Presupuestos:
  - RSS growth < 50MB tras 100 ciclos
  - workers al final = 0
  - procesos externos = 0
  - conexiones no cerradas = 0
  - warnings críticos = 0
"""
import gc
import os
import re
import sys
import threading
import tracemalloc
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

CRITICAL_PATTERNS = [
    re.compile(r"ReferenceError", re.IGNORECASE),
    re.compile(r"TypeError", re.IGNORECASE),
    re.compile(r"Binding loop", re.IGNORECASE),
    re.compile(r"Cannot assign to", re.IGNORECASE),
    re.compile(r"module is not installed", re.IGNORECASE),
    re.compile(r"Timers cannot be started", re.IGNORECASE),
    re.compile(r"Timers cannot be stopped", re.IGNORECASE),
    re.compile(r"Failed to load component", re.IGNORECASE),
]

WHITELIST_PATTERNS = ["QML import", "file:///", "module使用的是"]


def _is_critical(msg):
    for w in WHITELIST_PATTERNS:
        if w in msg:
            return False
    return any(p.search(msg) for p in CRITICAL_PATTERNS)


def _get_rss_mb():
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    return 0.0


def _count_threads():
    return threading.active_count()


def _count_external_processes():
    import subprocess
    try:
        result = subprocess.run(
            ["ps", "--ppid", str(os.getpid()), "-o", "pid,comm"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")[1:] if result.stdout.strip() else []
        return [line.split()[-1] for line in lines if line.split()[-1] not in ("ps", "sh")]
    except Exception:
        return []


def _count_db_connections():
    import gc as gc_module
    count = 0
    for obj in gc_module.get_objects():
        if hasattr(obj, "execute") and hasattr(obj, "cursor"):
            try:
                if hasattr(obj, "closed") and not obj.closed:
                    count += 1
            except Exception:
                pass
    return count


def _collect_qml_warnings() -> list[str]:
    return list(getattr(_collect_qml_warnings, "_warnings", []))


_warning_collector = []


def _qml_message_handler(msg_type, context, message):
    if _is_critical(message):
        _warning_collector.append(message)


class NavigationCycler:
    ROUTES = [
        "library", "library/albums", "library/artists", "queue",
        "audio_lab", "audio_lab_overview", "settings", "home",
    ]

    def __init__(self, engine, registrar, all_bridges):
        self._engine = engine
        self._registrar = registrar
        self._bridges = all_bridges
        self._nav = all_bridges.get("navigation")
        self._cycle_count = 0
        self._warnings = []

    def run_cycles(self, n: int = 100) -> dict:
        from PySide6.QtCore import QCoreApplication
        rss_before = _get_rss_mb()
        threads_before = _count_threads()
        gc.collect()
        gc.collect()
        tracemalloc.start()
        mem_before = tracemalloc.get_traced_memory()

        for i in range(n):
            for route in self.ROUTES:
                if self._nav and hasattr(self._nav, 'navigate'):
                    self._nav.navigate(route)
                for _ in range(5):
                    QCoreApplication.processEvents()
            self._cycle_count = i + 1
            gc.collect()

        mem_after = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss_after = _get_rss_mb()
        threads_after = _count_threads()

        leaked_objects_before = len(gc.get_objects())
        gc.collect()
        leaked_objects_after = len(gc.get_objects())

        external_procs = _count_external_processes()
        db_conns = _count_db_connections()

        audit = self._registrar.audit() if hasattr(self._registrar, 'audit') else {}
        duplicates = audit.get("duplicates", [])

        stale_callbacks = self._detect_stale_callbacks()

        result = {
            "cycles_completed": self._cycle_count,
            "rss_before_mb": round(rss_before, 2),
            "rss_after_mb": round(rss_after, 2),
            "rss_growth_mb": round(rss_after - rss_before, 2),
            "rss_growth_ok": (rss_after - rss_before) < 50.0,
            "threads_before": threads_before,
            "threads_after": threads_after,
            "threads_ok": threads_after == 0,
            "external_processes": external_procs,
            "external_processes_ok": len(external_procs) == 0,
            "db_connections_open": db_conns,
            "db_connections_ok": db_conns == 0,
            "leaked_objects": max(0, leaked_objects_after - leaked_objects_before),
            "traced_memory_before": mem_before[0],
            "traced_memory_after": mem_after[0],
            "critical_warnings": list(_warning_collector),
            "critical_warnings_ok": len(_warning_collector) == 0,
            "duplicate_context_properties": duplicates,
            "duplicates_ok": len(duplicates) == 0,
            "stale_callbacks": stale_callbacks,
            "stale_callbacks_ok": len(stale_callbacks) == 0,
        }
        return result

    def _detect_stale_callbacks(self):
        stale = []
        import gc as gc_module
        for obj in gc_module.get_objects():
            if hasattr(obj, 'callbacks') and isinstance(obj.callbacks, dict):
                for cb_key, cb_val in obj.callbacks.items():
                    if hasattr(cb_val, '__self__') and cb_val.__self__ is None:
                        stale.append(str(cb_key)[:80])
        return stale


def run() -> dict:
    from PySide6.QtCore import qInstallMessageHandler, QCoreApplication
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
    from PySide6.QtCore import QUrl

    qInstallMessageHandler(_qml_message_handler)

    if not QCoreApplication.instance():
        QCoreApplication(sys.argv)

    from ui_qml_bridge.qml_main import _create_services
    from ui_qml_bridge.bridge_factory import BridgeFactory
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.cover_bridge import CoverBridge

    services = _create_services()
    engine = QQmlApplicationEngine()
    registrar = ContextRegistrar(engine)

    factory = BridgeFactory(services)
    factory.create_navigation_bridge()
    all_bridges = factory.create_all()

    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = all_bridges.get(bridge_key)
        if bridge is not None:
            registrar.register(qml_name, bridge)

    app_state = all_bridges.get("app_state")
    if app_state:
        app_state.setServiceAvailability(
            services.player_service is not None,
            services.db is not None,
            "available" if services.player_service else "unavailable",
        )

    qmlRegisterType(CoverBridge, "MichiCover", 1, 0, "CoverBridge")

    qml_dir = REPO / "ui_qml"
    engine.addImportPath(str(qml_dir))
    main_qml = qml_dir / "Main.qml"
    if not main_qml.exists():
        return {"error": f"Main.qml not found at {main_qml}"}

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    root_objects = engine.rootObjects()

    if not root_objects:
        return {"error": "No QML root objects"}

    cycler = NavigationCycler(engine, registrar, all_bridges)
    nav_result = cycler.run_cycles(100)

    audit = registrar.audit() if hasattr(registrar, 'audit') else {}
    duplicates = audit.get("duplicates", [])

    result = {**nav_result, "root_objects": len(root_objects)}
    if duplicates:
        result["duplicate_context_properties"] = duplicates

    return result


def main():
    if "--json" in sys.argv:
        result = run()
        import json as _json
        print(_json.dumps(result))
        return 0

    result = run()

    print(f"\n{'='*60}")
    print("  QML Runtime Quality Audit")
    print(f"{'='*60}")

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return 1

    print(f"  Cycles completed:          {result['cycles_completed']}")
    print(f"  RSS before (MB):           {result['rss_before_mb']}")
    print(f"  RSS after (MB):            {result['rss_after_mb']}")
    print(f"  RSS growth (MB):           {result['rss_growth_mb']}")
    print(f"  RSS growth OK (<50MB):     {'PASS' if result['rss_growth_ok'] else 'FAIL'}")
    print(f"  Threads before:            {result['threads_before']}")
    print(f"  Threads after:             {result['threads_after']}")
    print(f"  Threads OK (=0):           {'PASS' if result['threads_ok'] else 'FAIL'}")
    print(f"  External processes:        {result['external_processes']}")
    print(f"  Ext processes OK (=0):     {'PASS' if result['external_processes_ok'] else 'FAIL'}")
    print(f"  DB connections open:       {result['db_connections_open']}")
    print(f"  DB connections OK (=0):    {'PASS' if result['db_connections_ok'] else 'FAIL'}")
    print(f"  Leaked objects:            {result['leaked_objects']}")
    print(f"  Critical warnings:         {len(result['critical_warnings'])}")
    print(f"  Critical warnings OK (=0): {'PASS' if result['critical_warnings_ok'] else 'FAIL'}")
    print(f"  Duplicate context props:   {result['duplicate_context_properties']}")
    print(f"  Duplicates OK (=0):        {'PASS' if result['duplicates_ok'] else 'FAIL'}")
    print(f"  Stale callbacks:           {len(result.get('stale_callbacks', []))}")
    print(f"  Stale callbacks OK (=0):   {'PASS' if result.get('stale_callbacks_ok', True) else 'FAIL'}")

    all_ok = (
        result['rss_growth_ok']
        and result['threads_ok']
        and result['external_processes_ok']
        and result['db_connections_ok']
        and result['critical_warnings_ok']
        and result['duplicates_ok']
        and result.get('stale_callbacks_ok', True)
    )
    print(f"\n{'='*60}")
    print(f"  OVERALL: {'PASSED' if all_ok else 'FAILED'}")
    print(f"{'='*60}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
