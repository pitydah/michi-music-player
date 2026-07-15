import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
=======
import QtQuick.Controls as QQC2
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import "../theme"

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property string title: "Error"
    property string message: "Ocurrió un error inesperado."
    property string details: ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string title: "No se pudo completar la operación"
    property string message: ""
>>>>>>> Stashed changes
    property string errorCode: ""
    property string errorSource: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool showRetry: true
    property bool reducedMotion: false

    signal retryRequested()
    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "ErrorState"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "") + (errorCode ? ". Código: " + errorCode : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "!"
            color: MichiTheme.colors.error
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            font.pixelSize: 40
            font.weight: MichiTheme.typography.weightBold
            visible: true
=======
=======
>>>>>>> Stashed changes
=======
    property string title: "Error"
    property string message: "Ocurrió un error inesperado."
    property string details: ""
    property string errorCode: ""
    property string errorSource: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool showRetry: true
    property bool reducedMotion: false

    signal retryRequested()
    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "ErrorState"

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "") + (errorCode ? ". Código: " + errorCode : "")

    implicitWidth: childrenColumn.implicitWidth
    implicitHeight: childrenColumn.implicitHeight

    Column {
        id: childrenColumn
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width * 0.85)
        spacing: MichiTheme.spacing.md

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "!"
            color: MichiTheme.colors.error
            font.pixelSize: 40
            font.weight: MichiTheme.typography.weightBold
            visible: true
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
<<<<<<< Updated upstream
<<<<<<< Updated upstream
            width: Math.min(implicitWidth, 460)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
            width: Math.min(implicitWidth, 460)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
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
<<<<<<< Updated upstream
            width: Math.min(Math.max(implicitWidth, 240), 460)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
            width: Math.min(Math.max(implicitWidth, 240), 460)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            visible: text !== ""
>>>>>>> Stashed changes
        }

        Item {
            width: 1
            height: MichiTheme.spacing.xs
        }

        QQC2.AbstractButton {
            id: expander
            anchors.horizontalCenter: parent.horizontalCenter
            text: (root.details !== "" || root.errorCode !== "" || root.errorSource !== "")
                  ? (detailsText.visible ? "Ocultar detalles" : "Ver detalles") : ""
            visible: text !== ""
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.Button
            Accessible.name: text

            contentItem: Text {
                text: parent.text
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }

            background: Item {}

            onClicked: detailsText.visible = !detailsText.visible
        }

        Column {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
        }

        Item {
            width: 1
            height: MichiTheme.spacing.xs
        }

        QQC2.AbstractButton {
            id: expander
            anchors.horizontalCenter: parent.horizontalCenter
            text: (root.details !== "" || root.errorCode !== "" || root.errorSource !== "")
                  ? (detailsText.visible ? "Ocultar detalles" : "Ver detalles") : ""
            visible: text !== ""
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.Button
            Accessible.name: text

            contentItem: Text {
                text: parent.text
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }

            background: Item {}

            onClicked: detailsText.visible = !detailsText.visible
        }

        Column {
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            id: detailsText
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            spacing: MichiTheme.spacing.xs
            visible: false

            Text {
                width: parent.width
                text: root.errorSource ? "Origen: " + root.errorSource : ""
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.errorCode ? "Código: " + root.errorCode : ""
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }

            Text {
                width: parent.width
                text: root.details
                color: MichiTheme.colors.textMeta
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                visible: text !== ""
            }
        }

        Row {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm

            MichiButton {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                text: root.primaryActionText
                visible: root.primaryActionText !== ""
                onClicked: root.primaryActionRequested()
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.retryText
                variant: "primary"
                onClicked: root.retryRequested()
>>>>>>> Stashed changes
            }

            MichiButton {
                text: root.secondaryActionText
                variant: "ghost"
<<<<<<< Updated upstream
=======
                visible: text !== ""
                onClicked: root.secondaryRequested()
=======
                text: root.primaryActionText
                visible: root.primaryActionText !== ""
                onClicked: root.primaryActionRequested()
            }

            MichiButton {
                text: root.secondaryActionText
                variant: "ghost"
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                visible: root.secondaryActionText !== ""
                onClicked: root.secondaryActionRequested()
            }

            MichiButton {
                text: "Reintentar"
                variant: "primary"
                visible: root.showRetry && root.primaryActionText === ""
                onClicked: root.retryRequested()
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
