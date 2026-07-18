import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Job Status Banner"
    objectName: "jobStatusBanner"
    focus: true
    id: root
    property var jobBridge: typeof jobBridge !== "undefined" ? jobBridge : null
    property int _activeCount: 0

    height: _activeCount > 0 ? 32 : 0
    color: MichiTheme.colors.surfaceCard
    visible: _activeCount > 0
    Behavior on height { NumberAnimation { duration: 150 } }

    Timer {
        interval: 1000; running: root.jobBridge !== null; repeat: true
        onTriggered: {
            if (root.jobBridge) root._activeCount = root.jobBridge.activeCount || 0
        }
    }

    Row {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm
        visible: _activeCount > 0

        BusyIndicator { running: true; width: 16; height: 16 }
        Label {
            text: _activeCount + " trabajo" + (_activeCount > 1 ? "s" : "") + " activo" + (_activeCount > 1 ? "s" : "")
            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.captionSize
        }
        Label {
            text: qsTr("(ver Jobs)"); color: MichiTheme.colors.accentBlue
            font.pixelSize: MichiTheme.typography.captionSize; font.underline: true
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("jobs") }
    }
}
