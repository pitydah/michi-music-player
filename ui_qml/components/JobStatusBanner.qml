import QtQuick
import QtQuick.Controls
import "../theme"

Rectangle {
    Accessible.role: Accessible.Button
    Accessible.name: _activeCount > 0
                     ? qsTr("%1 trabajos activos. Abrir trabajos.").arg(_activeCount)
                     : qsTr("Sin trabajos activos")
    objectName: "jobStatusBanner"
    id: root
    property var jobs: typeof jobBridge !== "undefined" ? jobBridge : null
    // Bound directly to the bridge property (notify=jobsChanged) — no polling.
    property int _activeCount: root.jobs ? (root.jobs.activeCount || 0) : 0

    height: _activeCount > 0 ? MichiTheme.minimumInteractiveSize : 0
    color: MichiTheme.colors.surfaceCard
    visible: _activeCount > 0
    activeFocusOnTab: visible
    border.width: activeFocus ? MichiTheme.focusWidth : 0
    border.color: MichiTheme.colors.borderFocus
    Behavior on height { NumberAnimation { duration: 150 } }

    function openJobs() {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("jobs")
    }

    Accessible.onPressAction: root.openJobs()
    Keys.onReturnPressed: root.openJobs()
    Keys.onSpacePressed: root.openJobs()

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
        onClicked: root.openJobs()
    }
}
