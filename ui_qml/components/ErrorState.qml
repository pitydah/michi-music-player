import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string title: "No se pudo completar la operación"
    property string message: ""
    property string errorCode: ""
    property string errorSource: ""
    property bool detailsExpanded: false
    property string retryText: "Reintentar"
    property string secondaryText: ""
    property string objectName: "errorState"

    signal retryRequested()
    signal secondaryRequested()

    Accessible.role: Accessible.Alert
    Accessible.name: root.title
    Accessible.description: root.message + (root.errorCode !== "" ? ". Código: " + root.errorCode : "")

    Keys.onEscapePressed: {
        root.detailsExpanded = !root.detailsExpanded
    }

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: Math.min(implicitWidth, 400)

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "\u26A0"
            font.pixelSize: MichiTheme.typography.heroTitleSize
            color: MichiTheme.colors.error
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            radius: MichiTheme.radiusSm
            color: MichiTheme.colors.badgeDangerBg
            visible: root.detailsExpanded && (root.errorCode !== "" || root.errorSource !== "")

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.xs

                Text {
                    text: root.errorCode !== "" ? "Código: " + root.errorCode : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.family: "monospace"
                    visible: text !== ""
                }

                Text {
                    text: root.errorSource !== "" ? "Origen: " + root.errorSource : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.captionSize
                    font.family: "monospace"
                    visible: text !== ""
                }
            }
        }

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.retryText
                variant: "primary"
                onClicked: root.retryRequested()
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.secondaryText
                variant: "ghost"
                visible: text !== ""
                onClicked: root.secondaryRequested()
            }
        }
    }
}
