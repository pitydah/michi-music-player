import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Unavailable State"
    objectName: "unavailableState"
    focus: true
    id: root

    property string title: "No disponible"
    property string message: "Esta función no está disponible en este momento."
    property string details: ""
    property string iconText: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""

    signal primaryActionRequested()
    signal secondaryActionRequested()


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
            font.pixelSize: MichiTheme.typography.heroTitleSize
            visible: true
            Accessible.role: Accessible.Icon
            Accessible.name: "No disponible"
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(implicitWidth, 460)
            text: root.title
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.message
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(Math.max(implicitWidth, 240), 460)
            text: root.details
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: MichiTheme.spacing.sm
            visible: root.primaryActionText !== "" || root.secondaryActionText !== ""

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: root.primaryActionText
                visible: text !== ""
                onClicked: root.primaryActionRequested()
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            MichiButton {
                text: root.secondaryActionText
                variant: "ghost"
                visible: text !== ""
                onClicked: root.secondaryActionRequested()
            }
        }
    }
}
