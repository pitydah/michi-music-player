import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string title: "No disponible"
    property string message: "Esta función no está disponible en el estado actual."
    property string explanation: ""
    property string actionText: ""
    property string objectName: "unavailableState"

    signal actionRequested()

    Accessible.role: Accessible.Alert
    Accessible.name: root.title
    Accessible.description: root.message + (root.explanation !== "" ? ". " + root.explanation : "")

    Keys.onReturnPressed: {
        if (actionText !== "") root.actionRequested()
    }
    Keys.onSpacePressed: {
        if (actionText !== "") root.actionRequested()
    }

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.lg
        width: Math.min(implicitWidth, 400)

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "\u26D4"
            font.pixelSize: MichiTheme.typography.heroTitleSize
            color: MichiTheme.colors.textMuted
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
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.explanation
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            visible: text !== ""
        }

        MichiButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.actionText
            variant: "primary"
            visible: text !== ""
            onClicked: root.actionRequested()
        }
    }
}
