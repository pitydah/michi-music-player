import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string trackTitle: "—"
    property string trackArtist: ""
    property string trackAlbum: ""
    property bool isPlaying: false
    property bool backendAvailable: true

    implicitHeight: 44

    Column {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 2

        Text {
            text: root.trackTitle
            color: root.isPlaying ? MichiTheme.colors.textPrimary : MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
            width: parent.width
        }

        Text {
            text: root.trackArtist ? root.trackArtist + (root.trackAlbum ? " · " + root.trackAlbum : "") : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            elide: Text.ElideRight
            width: parent.width
            visible: text !== ""
        }
    }
}
