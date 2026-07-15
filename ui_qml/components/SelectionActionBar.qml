import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: root

    property int selectedCount: 0
    property string clearText: "Limpiar selección"
    property var actionModels: []
    property string objectName: "selectionActionBar"

    signal clearRequested()
    signal actionTriggered(int index)

    height: root.selectedCount > 0 ? 56 : 0
    color: MichiTheme.colors.surfaceToolbar
    radius: MichiTheme.radiusMd
    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderCard
    visible: root.selectedCount > 0
    clip: true

    Accessible.role: Accessible.ToolBar
    Accessible.name: root.selectedCount + " elementos seleccionados"

    Behavior on height {
        NumberAnimation {
            duration: MichiTheme.motion.normal
            easing.type: Easing.OutCubic
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.lg
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.xs

        Text {
            text: root.selectedCount + " seleccionado" + (root.selectedCount !== 1 ? "s" : "")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            Layout.fillWidth: true
        }

        Repeater {
            model: root.actionModels
            delegate: MichiButton {
                text: modelData.text || ""
                variant: modelData.variant || "ghost"
                iconSource: modelData.iconSource || ""
                onClicked: root.actionTriggered(index)
                Accessible.name: modelData.accessibleName || modelData.text || ""
            }
        }

        MichiButton {
            text: root.clearText
            variant: "ghost"
            onClicked: root.clearRequested()
            Accessible.name: root.clearText
        }
    }
}
