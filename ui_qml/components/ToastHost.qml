import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Toast Host"
    objectName: "toastHost"
    focus: true
    id: root

    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    MichiToast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: MichiTheme.spacing.xxl
        message: root.notif ? (root.notif.message || "") : ""
        kind: root.notif ? (root.notif.kind || "info") : "info"
        visible: root.notif ? (root.notif.visible || false) : false

        onDismissed: {
            if (root.notif && typeof root.notif.dismiss === "function")
                root.notif.dismiss()
        }
    }
}
