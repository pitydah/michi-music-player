#!/usr/bin/env python3
"""Full QML runtime smoke test — loads Main.qml, checks for semantic QML warnings."""
import sys
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

PASSED = []
FAILED = []
WARNINGS = []


def check(name: str, ok: bool, detail: str = ""):
    if ok:
        PASSED.append(name)
        print(f"  [PASS] {name}")
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name}: {detail}")


# ── Critical QML warning patterns ──
CRITICAL_PATTERNS = [
    re.compile(r"ReferenceError", re.IGNORECASE),
    re.compile(r"TypeError", re.IGNORECASE),
    re.compile(r"Cannot assign to", re.IGNORECASE),
    re.compile(r"Cannot read property", re.IGNORECASE),
    re.compile(r"is not a function", re.IGNORECASE),
    re.compile(r"Binding loop", re.IGNORECASE),
    re.compile(r"no signal of the target matches", re.IGNORECASE),
    re.compile(r"Cannot anchor", re.IGNORECASE),
    re.compile(r"Failed to load component", re.IGNORECASE),
    re.compile(r"module is not installed", re.IGNORECASE),
    re.compile(r"QAbstractItemModel", re.IGNORECASE),
    re.compile(r"beginInsertRows", re.IGNORECASE),
    re.compile(r"endInsertRows", re.IGNORECASE),
    re.compile(r"Timers cannot be started", re.IGNORECASE),
    re.compile(r"Timers cannot be stopped", re.IGNORECASE),
]

WHITELIST = [
    "QML import",  # benign
    "module使用的是",  # translation
    "file:///",     # path info
]


def _is_critical(msg: str) -> bool:
    for w in WHITELIST:
        if w in msg:
            return False
    return any(p.search(msg) for p in CRITICAL_PATTERNS)


def _qml_message_handler(msg_type, context, message):
    if _is_critical(message):
        FAILED.append(f"QML WARNING: {message}")
        print(f"  [FAIL] QML: {message}")
    elif msg_type < 2:  # QtDebugMsg, QtInfoMsg
        pass
    else:
        WARNINGS.append(message)


def main():
    print("# QML Full Runtime Smoke Test\n")

    from PySide6.QtCore import qInstallMessageHandler, QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
    from PySide6.QtCore import QUrl

    qInstallMessageHandler(_qml_message_handler)

    app = QGuiApplication(sys.argv)

    from ui_qml_bridge.qml_main import _create_services
    from ui_qml_bridge.bridge_factory import BridgeFactory
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.cover_bridge import CoverBridge

    services = _create_services()
    check("Services created", True)

    engine = QQmlApplicationEngine()
    registrar = ContextRegistrar(engine)

    factory = BridgeFactory(services)
    factory.create_navigation_bridge()

    all_bridges = factory.create_all()
    check("BridgeFactory.create_all()", True)

    duplicate_actions = len([b for b in all_bridges.values() if hasattr(b, '_actions')])
    check("No duplicate action_registry", duplicate_actions <= 1,
          f"found {duplicate_actions}")

    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = all_bridges.get(bridge_key)
        if bridge is not None:
            registrar.register(qml_name, bridge)
        else:
            print(f"  [WARN] Bridge '{bridge_key}' not created")

    eq_bridge = factory.get("eq")
    if eq_bridge:
        registrar.register("eqBridge", eq_bridge)

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
        check("Main.qml exists", False, str(main_qml))
        return

    engine.load(QUrl.fromLocalFile(str(main_qml)))

    root_objects = engine.rootObjects()
    check("QML root objects created", len(root_objects) > 0,
          f"got {len(root_objects)}")

    audit = registrar.audit()
    check("No duplicate context properties", len(audit["duplicates"]) == 0,
          f"duplicates: {audit['duplicates']}")

    # ── Navigate all registered routes ──
    ROUTES = [
        "home", "library", "playlists", "radio", "lyrics", "mix", "settings",
        "devices", "connections", "home_audio", "eq", "queue", "history",
        "diagnostics", "library_sources",
    ]
    nav = all_bridges.get("navigation")
    if nav and hasattr(nav, 'navigate') and root_objects:
        for route in ROUTES:
            try:
                nav.navigate(route)
                for _ in range(10):
                    app.processEvents()
            except Exception as e:
                FAILED.append(f"Route '{route}': {e}")
                print(f"  [FAIL] Route '{route}': {e}")
        check("All routes navigated", True)
    else:
        check("Navigation available", nav is not None)

    if root_objects:
        QTimer.singleShot(500, app.quit)
        app.exec()
        check("App ran without crash", True)

    print("\n## Results")
    print(f"Passed: {len(PASSED)}")
    print(f"Failed: {len(FAILED)}")
    print(f"Warnings: {len(WARNINGS)}")

    if FAILED:
        print("\nFailed checks:")
        for f in FAILED:
            print(f"  - {f}")

    if WARNINGS:
        print(f"\nNon-critical warnings ({len(WARNINGS)}):")
        for w in WARNINGS[:5]:
            print(f"  - {w}")

    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
