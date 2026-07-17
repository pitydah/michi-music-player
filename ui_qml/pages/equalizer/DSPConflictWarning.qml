import QtQuick
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "DSPConflict Warning"
    objectName: "dSPConflictWarning"
    focus: true
    id: root

    property string message: ""

    implicitHeight: visible ? 60 : 0

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        variant: "status"

        Row {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.sm

            Text {
                text: "\u26A0"
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root.message
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width - 40
            }
        }
    }
}
