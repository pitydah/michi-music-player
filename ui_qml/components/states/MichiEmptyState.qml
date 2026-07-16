import QtQuick
import QtQuick.Controls
import "../../theme"
import ".."

Column {
    id: root

    property string title: "Sin contenido"
    property string message: ""
    property string iconName: "library"
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool busy: false
    property string details: ""
    property bool reducedMotion: false

    signal primaryActionRequested()
    signal secondaryActionRequested()

    spacing: MichiTheme.spacing.md
    width: Math.min(implicitWidth, 480)

    Accessible.role: Accessible.StaticText
    Accessible.name: title
    Accessible.description: message + (details !== "" ? ". " + details : "")

    MichiIcon {
        anchors.horizontalCenter: parent.horizontalCenter
        iconName: root.iconName
        accessibleName: root.title
        iconSize: 28
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
        visible: text !== ""
    }

    MichiProgressBar {
        Accessible.role: Accessible.ProgressBar

        activeFocusOnTab: true

        anchors.horizontalCenter: parent.horizontalCenter
        width: 160
        indeterminate: true
        visible: root.busy
        reducedMotion: root.reducedMotion
        accessibleName: root.title
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: MichiTheme.spacing.sm
        visible: root.primaryActionText !== "" || root.secondaryActionText !== ""
            Accessible.role: Accessible.Button

            activeFocusOnTab: true


        MichiButton {
            text: root.primaryActionText
            Accessible.role: Accessible.Button

            activeFocusOnTab: true

            visible: text !== ""
            onClicked: root.primaryActionRequested()
        }
        MichiButton {
            text: root.secondaryActionText
            variant: "ghost"
            visible: text !== ""
            onClicked: root.secondaryActionRequested()
        }
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
}
