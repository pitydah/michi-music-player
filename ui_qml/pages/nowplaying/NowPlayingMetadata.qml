import QtQuick
import QtQuick.Controls
import "../../theme"

Item {
    property var ps: null

    implicitHeight: metadataColumn.height

    Column {
        id: metadataColumn
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 4

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.ps && root.ps.trackTitle && root.ps.trackTitle !== "—"
                  ? root.ps.trackTitle : "Sin reproducción"
            color: root.ps && root.ps.isPlaying ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            width: parent.width
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.ps && root.ps.trackArtist ? root.ps.trackArtist : ""
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.ps && root.ps.trackAlbum ? root.ps.trackAlbum : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
        }
    }
}
