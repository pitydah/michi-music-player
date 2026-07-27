import QtQuick
import QtQuick.Controls as QQC2
import "../theme"

Item {
    id: root

    property string title: qsTr("No se pudo completar la operación")
    property string message: qsTr("Ocurrió un error inesperado.")
    property string details: ""
    property string errorCode: ""
    property string errorSource: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool showRetry: true
    property bool reducedMotion: false
    property bool detailsExpanded: false

    signal retryRequested()
    signal primaryActionRequested()
    signal secondaryActionRequested()

    readonly property bool hasDetails: details !== "" || errorCode !== "" || errorSource !== ""

    Accessible.role: Accessible.AlertMessage
    Accessible.name: title
    Accessible.description: message + (details ? ". " + details : "")
                            + (errorCode ? ". Código: " + errorCode : "")

    implicitWidth: stateColumn.implicitWidth
    implicitHeight: stateColumn.implicitHeight

    Column {
        id: stateColumn
        anchors.centerIn: parent
        width: Math.min(480, parent.width * 0.86)
        spacing: MichiTheme.spacing.md

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64
            height: 64
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.errorSurface
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.errorBorder

            MichiIcon {
                anchors.centerIn: parent
                source: "../../icons/states/error.svg"
                size: 28
                color: MichiTheme.colors.error
                accessibleName: qsTr("Error")
            }
        }

        Text {
            width: parent.width
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            width: parent.width
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        QQC2.AbstractButton {
            id: detailsButton
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.detailsExpanded ? qsTr("Ocultar detalles") : qsTr("Ver detalles")
            visible: root.hasDetails
            implicitWidth: detailsLabel.implicitWidth + MichiTheme.spacing.lg * 2
            implicitHeight: MichiTheme.minimumInteractiveSize
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Accessible.name: text
            onClicked: root.detailsExpanded = !root.detailsExpanded

            background: Rectangle {
                radius: MichiTheme.radius.sm
                color: detailsButton.down ? MichiTheme.colors.surfacePressed
                     : detailsButton.hovered ? MichiTheme.colors.surfaceHover : "transparent"
                border.width: detailsButton.activeFocus ? MichiTheme.focusWidth : 0
                border.color: MichiTheme.colors.borderFocus
            }

            contentItem: Text {
                id: detailsLabel
                text: detailsButton.text
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        Rectangle {
            width: parent.width
            height: detailsColumn.implicitHeight + MichiTheme.spacing.md * 2
            visible: root.detailsExpanded && root.hasDetails
            radius: MichiTheme.radius.sm
            color: MichiTheme.colors.surfaceInput
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            Column {
                id: detailsColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.xs

                Text {
                    width: parent.width
                    text: root.errorSource ? qsTr("Origen: %1").arg(root.errorSource) : ""
                    color: MichiTheme.colors.textMeta
                    font.pixelSize: MichiTheme.typography.captionSize
                    wrapMode: Text.WordWrap
                    visible: text !== ""
                }
                Text {
                    width: parent.width
                    text: root.errorCode ? qsTr("Código: %1").arg(root.errorCode) : ""
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
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm
            visible: root.primaryActionText !== "" || root.secondaryActionText !== "" || root.showRetry

            MichiButton {
                text: root.secondaryActionText
                variant: "secondary"
                visible: text !== ""
                onClicked: root.secondaryActionRequested()
            }

            MichiButton {
                text: root.primaryActionText
                visible: text !== ""
                onClicked: root.primaryActionRequested()
            }

            MichiButton {
                text: qsTr("Reintentar")
                visible: root.showRetry && root.primaryActionText === ""
                onClicked: root.retryRequested()
            }
        }
    }
}
