import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Rectangle {
    id: root

    property int count: 0
    property var actions: []
    property bool visible_b: false

    objectName: "SelectionActionBar"

    Accessible.role: Accessible.ToolBar
    Accessible.name: count > 0 ? count + " elementos seleccionados" : "Barra de selección"
    Accessible.description: "Acciones disponibles para elementos seleccionados"

    height: root.visible_b ? 56 : 0
    radius: MichiTheme.radiusMd
    color: MichiTheme.colors.surfaceCardElevated
    border.width: MichiTheme.borderWidth
    border.color: MichiTheme.colors.borderCard
    visible: root.visible_b && count > 0
    clip: true
    z: 100

    Behavior on height {
        NumberAnimation {
            duration: MichiTheme.motionFast
            easing.type: Easing.OutCubic
        }
    }

    Row {
        id: contentRow
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.lg
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.sm

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.count + " seleccionado" + (root.count !== 1 ? "s" : "")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Item {
            width: 1
            height: 1
            Layout.fillWidth: true
        }

        Repeater {
            model: root.actions

            delegate: MichiIconButton {
                anchors.verticalCenter: parent.verticalCenter
                iconText: modelData.icon || ""
                tooltipText: modelData.label || modelData.text || ""
                accessibleName: modelData.label || modelData.text || ""
                enabled: modelData.enabled !== false
                onClicked: {
                    if (modelData.callback) modelData.callback()
                    if (modelData.action) modelData.action()
                }
            }
        }

        MichiIconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconText: "\u00D7"
            tooltipText: "Deseleccionar todo"
            accessibleName: "Limpiar selección"
            onClicked: root.count = 0
        }
    }
}
