import QtQuick
import QtQuick.Layouts
import "../media"
import "../theme"

ColumnLayout {
    id: albumMagazine
    objectName: "albumMagazineView"

    readonly property var heroAlbum: library.albums.length > 0 ? library.albums[0] : null

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    Item {
        Layout.fillWidth: true
        Layout.preferredHeight: 160

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (heroAlbum !== null)
                    library.select_album(heroAlbum.key)
            }
        }

        Artwork {
            anchors.fill: parent
            sourcePath: heroAlbum !== null && heroAlbum.hasArtwork ? heroAlbum.artworkPath : ""
            fallbackText: heroAlbum !== null ? heroAlbum.title : "?"
            requestedSize: 640
        }
    }

    Text {
        Layout.fillWidth: true
        text: heroAlbum !== null ? heroAlbum.title : ""
        font.pixelSize: MichiTheme.fontSizeTitle
        font.weight: MichiTheme.fontWeightBold
        color: MichiTheme.textPrimary
        elide: Text.ElideRight
    }

    Text {
        Layout.fillWidth: true
        text: heroAlbum !== null ? heroAlbum.artist + " · " + heroAlbum.trackCount + " tracks" : ""
        font.pixelSize: MichiTheme.fontSizeBody
        color: MichiTheme.textSecondary
        elide: Text.ElideRight
    }

    ListView {
        id: magazineRows
        objectName: "albumMagazineList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: library.albums
        clip: true
        spacing: MichiTheme.space8
        delegate: RowLayout {
            visible: index > 0
            width: magazineRows.width
            height: MichiTheme.controlHeightSmall
            spacing: MichiTheme.space8

            Artwork {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                sourcePath: modelData.hasArtwork ? modelData.artworkPath : ""
                fallbackText: modelData.title
                requestedSize: 64
            }

            Text {
                Layout.fillWidth: true
                text: modelData.title
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textPrimary
                elide: Text.ElideRight
            }

            Text {
                text: modelData.year > 0 ? "" + modelData.year : "Unknown"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: library.select_album(modelData.key)
            }
        }
    }
}
