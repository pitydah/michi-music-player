import QtQuick
import QtQuick.Controls
import "album" as AlbumViews

Item {
    id: root
    objectName: "albumGridPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Álbumes")

    property var albumModel: typeof libraryBridge !== "undefined" && libraryBridge
                             ? libraryBridge.albumModel : null
    property var bridge: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property int currentView: 0

    signal albumClicked(string albumKey, string title, string artist, int year)

    AlbumViews.AlbumViewHost {
        id: albumHost
        anchors.fill: parent
        albumModel: root.albumModel
        bridge: root.bridge
        currentView: root.currentView

        onViewChanged: function(index) {
            root.currentView = index
        }

        onAlbumClicked: function(key, title, artist, year) {
            root.albumClicked(key, title, artist, year)
            if (typeof navigationBridge !== "undefined" && navigationBridge && key)
                navigationBridge.navigateWithParams(
                    "library.album_detail",
                    { album_key: key }
                )
        }
    }
}
