import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string deviceAlias: ""
    property string deviceType: "desktop"
    property string deviceIp: ""
    property int devicePort: 0
    property bool paired: false

    signal connectClicked()

    implicitHeight: 80

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        hovered: mouseArea.containsMouse
        interactive: true

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            Rectangle {
                width: 40; height: 40; radius: MichiTheme.radiusSm; anchors.verticalCenter: parent.verticalCenter
                color: root.paired ? MichiTheme.colors.badgeActiveBg : MichiTheme.colors.accentSurface
                Text {
                    anchors.centerIn: parent
                    text: root.deviceAlias ? root.deviceAlias.charAt(0).toUpperCase() : "?"
                    color: root.paired ? MichiTheme.colors.success : MichiTheme.colors.accentBlue
                    font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold
                }
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs; width: parent.width - 120
                Text {
                    text: root.deviceAlias || "Dispositivo"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium; elide: Text.ElideRight; width: parent.width
                }
                Text {
                    text: root.deviceIp ? root.deviceIp + ":" + root.devicePort : root.deviceType
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; width: parent.width
                }
            }

            StatusBadge {
                anchors.verticalCenter: parent.verticalCenter
                text: root.paired ? "Vinculado" : "Detectado"
                kind: root.paired ? "success" : "info"
            }
        }
    }
}
