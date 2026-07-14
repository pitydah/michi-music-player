import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var albumModel: null
    property var bridge: null

    signal albumClicked(string albumKey, string title, string artist, int year)

    GridView {
        id: gridView
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        cellWidth: 180
        cellHeight: 220
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: AlbumCard {
            width: gridView.cellWidth - MichiTheme.spacing.md
            height: gridView.cellHeight - MichiTheme.spacing.md
            albumKey: model.albumKey || ""
            albumTitle: model.title || ""
            albumArtist: model.artist || ""
            albumYear: model.year || 0
            trackCount: model.trackCount || 0

            onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
        }
    }
}
