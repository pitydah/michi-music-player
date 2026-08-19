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

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiTheme.space12
        visible: library.selectedAlbumKey === ""

        Text {
            text: "Grid"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "grid" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "grid" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "grid"
            }
        }

        Text {
            text: "Cover"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "cover" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "cover" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "cover"
            }
        }

        Text {
            text: "Vinyl"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "vinyl" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "vinyl" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "vinyl"
            }
        }

        Text {
            text: "Timeline"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "timeline" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "timeline" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "timeline"
            }
        }

        Text {
            text: "Magazine"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "magazine" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "magazine" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "magazine"
            }
        }

        Text {
            text: "List"
            font.pixelSize: MichiTheme.fontSizeCaption
            font.weight: albumMode === "list" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
            color: albumMode === "list" ? MichiTheme.warning : MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: albumMode = "list"
            }
        }
    }

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
