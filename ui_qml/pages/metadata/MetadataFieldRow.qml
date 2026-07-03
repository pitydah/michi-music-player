import QtQuick
import QtQuick.Controls
import "../../theme"

Item {
    id: root

    property string fieldLabel: ""
    property string fieldValue: ""

    implicitHeight: 32

    Row {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.sm

        Text {
            width: parent.width * 0.30
            text: root.fieldLabel
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideRight
        }

        Text {
            width: parent.width * 0.65
            text: root.fieldValue
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideRight
        }
    }
}
