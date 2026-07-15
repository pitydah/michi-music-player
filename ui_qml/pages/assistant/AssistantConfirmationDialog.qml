import QtQuick
import QtQuick.Controls
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Layouts
=======
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import "../../theme"
import "../../components"

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool visible: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string title: "Confirmar acción"
    property string message: "¿Estás seguro de realizar esta acción?"
    property bool destructive: false
    property var actionDetails: ({})
    property bool open: false
    property int affectedCount: 0
=======
    property string actionName: ""
    property string actionDescription: ""
    property var affectedItems: []
    property bool destructive: false
    property bool visible: false
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    signal confirmed()
    signal cancelled()

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    anchors.fill: parent
    visible: root.visible
    z: 10000
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    visible: root.open
    focus: root.open
    objectName: "assistant.confirmation.dialog"
>>>>>>> Stashed changes

    Accessible.role: Accessible.Dialog
    Accessible.name: "Confirmar acción" + (destructive ? " - Acción destructiva" : "")
    Accessible.description: actionDescription

<<<<<<< Updated upstream
    Keys.onEscapePressed: root.cancelled()
=======
    Keys.onEscapePressed: {
        root.open = false
        root.cancelled()
    }

    Keys.onReturnPressed: {
        if (!root.destructive) {
            root.open = false
            root.confirmed()
        }
    }
=======
    anchors.fill: parent
    visible: root.visible
    z: 10000

    Accessible.role: Accessible.Dialog
    Accessible.name: "Confirmar acción" + (destructive ? " - Acción destructiva" : "")
    Accessible.description: actionDescription

    Keys.onEscapePressed: root.cancelled()
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        opacity: 0.8

        MouseArea {
            anchors.fill: parent
            onClicked: root.cancelled()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        z: 9990

        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.open = false
                root.cancelled()
            }
=======
        opacity: 0.8

        MouseArea {
            anchors.fill: parent
            onClicked: root.cancelled()
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        }
    }

    Rectangle {
        anchors.centerIn: parent
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        width: 400
        implicitHeight: dialogColumn.height + MichiTheme.spacing.xl * 2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        width: Math.min(400, parent.width * 0.9)
>>>>>>> Stashed changes
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
        focus: true

        Keys.onEscapePressed: root.cancelled()

        Column {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Text {
                width: parent.width
                text: root.destructive ? "⚠ Acción destructiva" : "Confirmar acción"
                color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.actionDescription || root.actionName
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Repeater {
                model: root.affectedItems
                visible: root.affectedItems.length > 0

                Rectangle {
                    width: parent.width
                    height: 28
                    radius: MichiTheme.radiusXs
                    color: MichiTheme.colors.surfaceSubtle

<<<<<<< Updated upstream
=======
                Column {
                    id: detailsColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: root.actionDetails ? Object.keys(root.actionDetails) : []

                        Row {
                            width: parent.width
                            spacing: MichiTheme.spacing.xs
                            Text {
                                text: modelData + ":"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.35
                                elide: Text.ElideRight
                            }
                            Text {
                                text: root.actionDetails[modelData] || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: parent.width * 0.60
                                elide: Text.ElideRight
                            }
                        }
=======
        width: 400
        implicitHeight: dialogColumn.height + MichiTheme.spacing.xl * 2
        radius: MichiTheme.radiusMd
        color: MichiTheme.colors.surfacePopup
        border.color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
        focus: true

        Keys.onEscapePressed: root.cancelled()

        Column {
            id: dialogColumn
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Text {
                width: parent.width
                text: root.destructive ? "⚠ Acción destructiva" : "Confirmar acción"
                color: root.destructive ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.actionDescription || root.actionName
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Repeater {
                model: root.affectedItems
                visible: root.affectedItems.length > 0

                Rectangle {
                    width: parent.width
                    height: 28
                    radius: MichiTheme.radiusXs
                    color: MichiTheme.colors.surfaceSubtle

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        elide: Text.ElideRight
                        width: parent.width - MichiTheme.spacing.md
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

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Text {
                width: parent.width
                text: "¿Estás seguro?"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            Item { height: 1; Layout.fillWidth: true }
>>>>>>> Stashed changes

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                layoutDirection: Qt.RightToLeft

<<<<<<< Updated upstream
=======
                Item { Layout.fillWidth: true }
=======
            Text {
                width: parent.width
                text: "¿Estás seguro?"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                layoutDirection: Qt.RightToLeft

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                MichiButton {
                    text: root.destructive ? "Eliminar" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    objectName: "confirmationDialogConfirm"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.confirmed()
                }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    objectName: "assistant.confirmation.cancel"
                    Accessible.name: "Cancelar acción"
                    onClicked: {
                        root.open = false
                        root.cancelled()
                    }
                }

                MichiButton {
                    text: root.destructive ? "Confirmar acción destructiva" : "Confirmar"
                    variant: root.destructive ? "danger" : "primary"
                    objectName: "assistant.confirmation.confirm"
                    Accessible.name: root.destructive ? "Confirmar acción destructiva" : "Confirmar acción"
                    Accessible.description: root.destructive ? "Esta acción no se puede deshacer" : ""
                    onClicked: {
                        root.open = false
                        root.confirmed()
                    }
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    objectName: "confirmationDialogCancel"
                    Accessible.name: "Cancelar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    onClicked: root.cancelled()
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
    }
}
