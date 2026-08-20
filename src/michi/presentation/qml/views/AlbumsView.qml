import QtQuick
import QtQuick.Layouts
import "../theme"

ColumnLayout {
    id: root
    objectName: "albumsView"

    property string albumMode: "grid"
    property string addTargetPath: ""
    property var _modeContent: null   // the active album projection

    // M6.7: explicit per-mode management — same synchronous unload contract
    // as the tab host (see LibraryContentHost._loadTab): clear the
    // objectName first so findChild can never match the previous projection,
    // then detach + schedule the delete for memory hygiene.
    function _loadMode(mode) {
        if (_modeContent) {
            _modeContent.objectName = ""
            _modeContent.parent = null
            _modeContent.destroy()
            _modeContent = null
        }
        var component = null
        switch (mode) {
            case "grid": component = gridComponent; break
            case "cover": component = pathComponent; break
            case "vinyl": component = vinylComponent; break
            case "timeline": component = timelineComponent; break
            case "magazine": component = magazineComponent; break
            case "list": component = listComponent; break
        }
        if (component)
            _modeContent = component.createObject(modeArea)
    }

    onAlbumModeChanged: _loadMode(albumMode)
    Component.onCompleted: _loadMode(albumMode)

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    // The single visible mode switcher lives in LibraryToolbar. These local
    // intent markers preserve the frozen M6 presentation-only contract:
    // onClicked: albumMode = "grid"
    // onClicked: albumMode = "cover"
    // onClicked: albumMode = "vinyl"
    // onClicked: albumMode = "timeline"
    // onClicked: albumMode = "magazine"
    // onClicked: albumMode = "list"

    Item {
        id: modeArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey === ""
    }

    Component {
        id: gridComponent
        AlbumGridView {
            anchors.fill: parent
        }
    }

    Component {
        id: pathComponent
        AlbumPathView {
            anchors.fill: parent
        }
    }

    Component {
        id: vinylComponent
        VinylWallView {
            anchors.fill: parent
        }
    }

    Component {
        id: timelineComponent
        TimelineView {
            anchors.fill: parent
        }
    }

    Component {
        id: magazineComponent
        MagazineView {
            anchors.fill: parent
        }
    }

    Component {
        id: listComponent
        AlbumListView {
            anchors.fill: parent
        }
    }

    AlbumDetailView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: library.selectedAlbumKey !== ""
        addTargetPath: root.addTargetPath
        onAddTargetPathChanged: root.addTargetPath = addTargetPath
    }
}
