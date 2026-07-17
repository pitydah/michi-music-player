import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Cancellation Banner"
    objectName: "cancellationBanner"
    focus: true
    id: root

    property string title: "Cancelando\u2026"
    property string message: ""
    property bool active: false
    property bool reducedMotion: false


    Accessible.description: message || "Una operación está siendo cancelada"

    height: active ? 40 : 0
    width: parent ? parent.width : implicitWidth
    color: MichiTheme.colors.warning
    radius: MichiTheme.radius.sm
    visible: active
    clip: true

    Behavior on height {
        NumberAnimation {
            duration: root.reducedMotion ? 0 : MichiTheme.motion.durationFast
            easing.type: Easing.OutCubic
        }
    }

    Row {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        QQC2.BusyIndicator {
            width: 16
            height: 16
            running: root.active
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            color: MichiTheme.colors.textOnAccent
            font.pixelSize: MichiTheme.typography.captionSize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.message
            color: MichiTheme.colors.textOnAccent
            font.pixelSize: MichiTheme.typography.captionSize
            visible: root.message !== ""
        }
    }
}
