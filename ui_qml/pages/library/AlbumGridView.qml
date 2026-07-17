import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Grid View"
    objectName: "albumGridView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null

    signal albumClicked(string albumKey, string title, string artist, int year)

    MichiResponsive { id: responsive; availableWidth: root.width }

    GridView {
        Accessible.role: Accessible.List

        Accessible.name: "Cuadrícula de álbumes"

        id: gridView
        activeFocusOnTab: true

        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        cellWidth: Math.max(MichiTheme.coverSizeSmall * 3, Math.floor((root.width - MichiTheme.spacing.md * 2 - MichiTheme.spacing.md * (responsive.columnCount - 1)) / responsive.columnCount))
        cellHeight: cellWidth + MichiTheme.spacing.xxxl + MichiTheme.typography.cardTitleSize + MichiTheme.typography.metaSize
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar { width: MichiTheme.spacing.sm; policy: ScrollBar.AsNeeded }

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
