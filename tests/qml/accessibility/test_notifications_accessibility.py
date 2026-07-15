from __future__ import annotations

"""MS: Specialized accessibility — Notifications domain."""


def test_notification_bridge_accessible():
    filepath = "ui_qml_bridge/notification_bridge.py"
    with open(filepath) as f:
        content = f.read()
    assert "QObject" in content


def test_notification_components_have_accessible():
    import os
    components = [
        "ui_qml/components/NotificationAnnouncement.qml",
        "ui_qml/components/NotificationBanner.qml",
        "ui_qml/components/NotificationItem.qml",
        "ui_qml/components/NotificationToast.qml",
    ]
    for comp in components:
        assert os.path.exists(comp), f"Missing: {comp}"
        with open(comp) as f:
            c = f.read()
        assert "Accessible" in c, f"No Accessible in {comp}"


def test_notification_components_keyboard():
    components = [
        "ui_qml/components/NotificationBanner.qml",
        "ui_qml/components/NotificationItem.qml",
        "ui_qml/components/NotificationToast.qml",
    ]
    for comp in components:
        with open(comp) as f:
            c = f.read()
        assert "focus" in c or "KeyNavigation" in c or "activeFocusOnTab" in c


def test_notification_progress_accessible():
    filepath = "ui_qml/components/NotificationProgressItem.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible" in content


def test_notification_cancel_accessible():
    filepath = "ui_qml/components/CancellationBanner.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Accessible" in content or "focus" in content
