import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
import QtQuick.Layouts
=======
import QtQuick.Controls as QQC2
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import "../theme"

Rectangle {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property int count: 0
    property var actions: []
    property bool visible_b: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property int selectedCount: 0
    property string clearText: "Limpiar selección"
    property var actionModels: []
    property string objectName: "selectionActionBar"
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
            duration: MichiTheme.motionFast
=======
            duration: MichiTheme.motion.normal
=======
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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            easing.type: Easing.OutCubic
        }
    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    Row {
        id: contentRow
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    RowLayout {
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        }

        Item {
            width: 1
            height: 1
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            Layout.fillWidth: true
        }

        Repeater {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
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

=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
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
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        MichiIconButton {
            anchors.verticalCenter: parent.verticalCenter
            iconText: "\u00D7"
            tooltipText: "Deseleccionar todo"
            accessibleName: "Limpiar selección"
            onClicked: root.count = 0
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
