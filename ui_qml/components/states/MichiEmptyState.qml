import QtQuick
import QtQuick.Controls
import "../../theme"
import ".."

Item {
    id: root

    property string title: qsTr("Sin contenido")
    property string message: ""
    property string iconName: "library"
    property url iconSource: ""
    property color iconColor: MichiTheme.colors.accentPrimary
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property bool busy: false
    property string details: ""
    property bool reducedMotion: false

    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitWidth: column.implicitWidth
    implicitHeight: column.implicitHeight

    Accessible.role: Accessible.StaticText
    Accessible.name: title
    Accessible.description: message + (details !== "" ? ". " + details : "")

    Column {
        id: column
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.md
        width: Math.min(implicitWidth, 480)

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64
            height: 64
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.accentGlowSubtle
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.accentSeparator

            MichiIcon {
                anchors.centerIn: parent
                iconName: root.iconName
                source: root.iconSource
                accessibleName: root.title
                iconSize: 28
                color: root.iconColor
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 5
                width: 18
                height: 2
                radius: 1
                color: root.iconColor
            }
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

            MichiButton {
                text: root.primaryActionText
                visible: text !== ""
                onClicked: root.primaryActionRequested()
            }
            MichiButton {
                text: root.secondaryActionText
                variant: "secondary"
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
}
