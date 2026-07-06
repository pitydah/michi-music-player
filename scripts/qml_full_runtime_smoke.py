#!/usr/bin/env python3
"""Full QML runtime smoke test — loads Main.qml with all bridges, checks for errors."""
import sys
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

PASSED = []
FAILED = []


def check(name: str, ok: bool, detail: str = ""):
    if ok:
        PASSED.append(name)
        print(f"  [PASS] {name}")
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name}: {detail}")


def main():
    print("# QML Full Runtime Smoke Test\n")

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl

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

    # Check for duplicates
    duplicate_actions = len([b for b in all_bridges.values() if hasattr(b, '_actions')])
    check("No duplicate action_registry", duplicate_actions <= 1,
          f"found {duplicate_actions}")

    # Register context properties from canonical bindings
    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = all_bridges.get(bridge_key)
        if bridge is not None:
            registrar.register(qml_name, bridge)
        else:
            print(f"  [WARN] Bridge '{bridge_key}' not created")

    # eqBridge is optional
    eq_bridge = factory.get("eq")
    if eq_bridge:
        registrar.register("eqBridge", eq_bridge)

    # Set service availability
    app_state = all_bridges.get("app_state")
    if app_state:
        app_state.setServiceAvailability(
            services.player_service is not None,
            services.db is not None,
            "available" if services.player_service else "unavailable",
        )

    from PySide6.QtQml import qmlRegisterType
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

    # Audit
    audit = registrar.audit()
    check("No duplicate context properties", len(audit["duplicates"]) == 0,
          f"duplicates: {audit['duplicates']}")

    # Process events briefly
    if root_objects:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, app.quit)
        app.exec()
        check("App ran without crash", True)

    print("\n## Results")
    print(f"Passed: {len(PASSED)}")
    print(f"Failed: {len(FAILED)}")

    if FAILED:
        print("\nFailed checks:")
        for f in FAILED:
            print(f"  - {f}")

    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
