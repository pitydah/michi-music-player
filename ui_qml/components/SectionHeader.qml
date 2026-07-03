import QtQuick
import "../theme"

Item {
    id: root

    property string text: ""
    property bool uppercase: false
    property bool showChevron: false

    implicitHeight: 28
    implicitWidth: parent ? parent.width : 200

    Row {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: MichiTheme.spacing.sm

        Text {
            text: root.uppercase ? root.text.toUpperCase() : root.text
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            font.letterSpacing: root.uppercase ? 0.5 : 0.0
        }

        Text {
            text: "›"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            visible: root.showChevron
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
