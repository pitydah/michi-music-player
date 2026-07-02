import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    property string trackTitle: "—"
    property string trackArtist: ""
    property string trackAlbum: ""
    property bool isPlaying: false

    implicitHeight: 44

    Column {
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        Text {
            text: root.trackTitle
            color: root.isPlaying ? MichiColors.textPrimary : MichiColors.textSecondary
            font.pixelSize: MichiTypography.bodySize
            font.weight: MichiTypography.weightMedium
            elide: Text.ElideRight
            width: 200
        }

        Text {
            text: root.trackArtist ? root.trackArtist + (root.trackAlbum ? " · " + root.trackAlbum : "") : ""
            color: MichiColors.textMuted
            font.pixelSize: MichiTypography.metaSize
            elide: Text.ElideRight
            width: 200
            visible: text !== ""
        }
    }
}
