import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album List View"
    objectName: "albumListView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null

    signal albumClicked(string albumKey, string title, string artist, int year)

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: "Lista de álbumes"

        activeFocusOnTab: true

        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiTheme.spacing.xs

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: MichiAlbumRow {
            width: parent.width
            title: model.title || ""
            artist: model.artist || ""
            year: model.year || 0
            trackCount: model.trackCount || 0

            onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
        }
    }

    function formatDuration(secs) {
        if (!secs) return ""
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
