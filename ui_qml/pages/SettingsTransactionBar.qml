import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"

Rectangle {
    id: root

    property var bridge: null
    property bool busy: false
    property string message: ""

    signal applyRequested()
    signal discardRequested()

    implicitHeight: visible ? contentRow.implicitHeight + MichiTheme.spacing.md * 2 : 0
    visible: bridge !== null && bridge.hasPendingChanges
    color: MichiTheme.colors.surfaceElevated
    radius: MichiTheme.radius.md
    border.width: 1
    border.color: MichiTheme.colors.warning

    Accessible.role: Accessible.ToolBar
    Accessible.name: qsTr("Cambios de ajustes pendientes")

    RowLayout {
        id: contentRow
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Label {
                text: bridge && bridge.pendingCount === 1
                      ? qsTr("1 cambio pendiente")
                      : qsTr("%1 cambios pendientes").arg(bridge ? bridge.pendingCount : 0)
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Label {
                text: root.message || qsTr("Los cambios ya están activos en esta sesión. Puedes confirmarlos o restaurar los valores anteriores.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        BusyIndicator {
            running: root.busy
            visible: root.busy
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
        }

        MichiButton {
            text: qsTr("Descartar")
            variant: "ghost"
            enabled: !root.busy
            onClicked: root.discardRequested()
        }

        MichiButton {
            text: qsTr("Aplicar cambios")
            variant: "primary"
            enabled: !root.busy
            onClicked: root.applyRequested()
        }
    }
}
