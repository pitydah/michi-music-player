import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string playlistTitle: ""
    property int trackCount: 0
    property string duration: ""
    property string coverKey: ""

    signal clicked()

    implicitWidth: 200; implicitHeight: 240

    GlassMaterial {
        anchors.fill: parent; radius: MichiTheme.radiusMd
        hovered: mouseArea.containsMouse; interactive: true
        MouseArea {
            id: mouseArea; anchors.fill: parent
            hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }

        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm

            Rectangle {
                width: parent.width; height: width; radius: MichiTheme.radiusSm
                color: Qt.rgba(1.0, 1.0, 1.0, 0.03); clip: true
                CoverBridge { anchors.fill: parent; coverKey: root.coverKey || root.playlistTitle || "PL" }
            }

            Text {
                text: root.playlistTitle; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight; width: parent.width
            }
            Text {
                text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
        }
    }
}
