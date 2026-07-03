import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string artistName: ""
    property int trackCount: 0
    property int albumCount: 0
    property string coverId: ""

    signal clicked()

    implicitWidth: 180
    implicitHeight: 200

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

            CoverImage {
                width: parent.width
                height: width
                coverRadius: MichiTheme.radiusPill
                coverKey: root.coverId || root.artistName || "ARTIST"
                showPlaceholder: true
            }

            Text {
                text: root.artistName
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                text: root.albumCount > 0 ? root.albumCount + " álbumes" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
            }
        }
    }
}
