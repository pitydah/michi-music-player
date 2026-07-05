import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    id: root

    property var albumModel: null
    property var bridge: null
    property int currentView: 0

    signal albumClicked(string albumKey, string title, string artist, int year)

    function reload() {
        viewLoader.active = false
        viewLoader.active = true
    }

    Loader {
        id: viewLoader
        anchors.fill: parent
        active: true
        source: {
            switch (root.currentView) {
                case 0: return "AlbumGridView.qml"
                case 1: return "AlbumCoverFlowView.qml"
                case 2: return "AlbumVinylWallView.qml"
                case 3: return "AlbumTimelineView.qml"
                case 4: return "AlbumMagazineView.qml"
                default: return "AlbumGridView.qml"
            }
        }

        onLoaded: {
            viewLoader.item.albumModel = root.albumModel
            viewLoader.item.bridge = root.bridge
            viewLoader.item.albumClicked.connect(root.albumClicked)
        }
    }
}
