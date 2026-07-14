import QtQuick
import QtQuick.Controls
import "../../theme"

Item {
    id: root

    property string fieldLabel: ""
    property string fieldValue: ""
    property string fieldKey: ""
    property bool editable: false
    signal valueChanged(string newValue)

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

        Loader {
            width: parent.width * 0.65
            sourceComponent: root.editable ? editComponent : displayComponent
        }
    }

    Component {
        id: displayComponent
        Text {
            width: parent.width
            text: root.fieldValue
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            anchors.verticalCenter: parent.verticalCenter
            elide: Text.ElideRight
        }
    }

    Component {
        id: editComponent
        TextField {
            width: parent.width
            text: root.fieldValue
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            anchors.verticalCenter: parent.verticalCenter
            onTextChanged: root.valueChanged(text)
        }
    }
}
