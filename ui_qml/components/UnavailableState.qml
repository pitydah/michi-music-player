import QtQuick
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
import QtQuick.Controls
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import "../theme"

Item {
    id: root

    property string title: "No disponible"
<<<<<<< Updated upstream
    property string message: "Esta función no está disponible en este momento."
    property string details: ""
    property string iconText: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
=======
<<<<<<< HEAD
    property string message: "Esta función no está disponible en el estado actual."
    property string explanation: ""
    property string actionText: ""
    property string objectName: "unavailableState"
>>>>>>> Stashed changes

    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "UnavailableState"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.iconText || "\u26A0"
            color: MichiTheme.colors.textMuted
<<<<<<< Updated upstream
            font.pixelSize: 36
            visible: true
=======
=======
    property string message: "Esta función no está disponible en este momento."
    property string details: ""
    property string iconText: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""

    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "UnavailableState"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.iconText || "\u26A0"
            color: MichiTheme.colors.textMuted
            font.pixelSize: 36
            visible: true
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
            width: Math.min(implicitWidth, 460)
=======
<<<<<<< HEAD
=======
            width: Math.min(implicitWidth, 460)
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
            width: Math.min(Math.max(implicitWidth, 240), 460)
=======
<<<<<<< HEAD
=======
            width: Math.min(Math.max(implicitWidth, 240), 460)
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.details
=======
<<<<<<< HEAD
            text: root.explanation
=======
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.details
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

<<<<<<< Updated upstream
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
=======
<<<<<<< HEAD
        MichiButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            variant: "primary"
            visible: text !== ""
            onClicked: root.actionRequested()
=======
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
>>>>>>> Stashed changes
            spacing: MichiTheme.spacing.sm
            visible: root.primaryActionText !== "" || root.secondaryActionText !== ""

            MichiButton {
                text: root.primaryActionText
                visible: text !== ""
                onClicked: root.primaryActionRequested()
            }

            MichiButton {
                text: root.secondaryActionText
                variant: "ghost"
                visible: text !== ""
                onClicked: root.secondaryActionRequested()
            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
