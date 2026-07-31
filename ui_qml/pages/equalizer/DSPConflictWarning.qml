import QtQuick
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("DSPConflict Warning")
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
                text: qsTr("\u26A0")
                color: MichiTheme.colors.warning
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
                Accessible.role: Accessible.Graphic
                Accessible.name: qsTr("Advertencia")
                Accessible.description: qsTr("Conflicto de DSP detectado")
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
