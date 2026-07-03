import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string albumTitle: ""
    property string albumArtist: ""
    property int trackCount: 0
    property string coverId: ""

    signal clicked()

    implicitWidth: 180
    implicitHeight: 240

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
            onClicked: root.clicked()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Rectangle {
                width: parent.width
                height: width
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.borderInner
                clip: true

                CoverBridge {
                    id: coverItem
                    anchors.fill: parent
                    coverKey: root.coverId || root.albumTitle || "COVER"
                    visible: true
                }
            }

            Text {
                text: root.albumTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width
            }

            Text {
                text: root.albumArtist
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                elide: Text.ElideRight
                width: parent.width
                visible: root.albumArtist !== ""
            }

            Text {
                text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }
        }
    }
}
