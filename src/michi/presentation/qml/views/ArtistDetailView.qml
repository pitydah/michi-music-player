import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    objectName: "artistDetailView"
    property string addTargetPath: ""

    spacing: MichiThemeState.contentGap
    visible: library.selectedArtistKey !== ""

    RowLayout {
        Layout.fillWidth: true
        spacing: MichiSpacing.lg

        Rectangle {
            Layout.preferredWidth: 92
            Layout.preferredHeight: 92
            radius: 46
            color: MichiSemanticColors.controlSurfaceStrong
            MichiIcon {
                anchors.centerIn: parent
                name: "artist"
                width: 32
                height: 32
                iconColor: MichiPalette.auroraCyan
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiButton {
                text: "Back"
                variant: "ghost"
                Layout.alignment: Qt.AlignLeft
                onClicked: library.clear_artist_selection()
            }
            MichiText {
                Layout.fillWidth: true
                text: library.artistName
                role: "display"
                elide: Text.ElideRight
            }
            MichiText {
                text: library.artistAlbumCount + " albums · "
                    + library.artistTrackCount + " tracks"
                role: "secondary"
            }
        }
    }

    MichiText {
        text: "Albums"
        role: "section"
        visible: library.artistAlbums.length > 0
    }

    GridView {
        id: artistAlbumsGrid
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? Math.min(220, contentHeight) : 0
        visible: library.artistAlbums.length > 0
        model: library.artistAlbums
        cellWidth: 176
        cellHeight: 214
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        delegate: AlbumCard {
            required property var modelData
            width: artistAlbumsGrid.cellWidth - MichiSpacing.sm
            album: modelData
            onActivated: library.select_album(modelData.key)
        }
    }

    MichiText { text: "Tracks"; role: "section" }

    ListView {
        id: artistTracksList
        Layout.fillWidth: true
        Layout.fillHeight: true
        model: library.artistTracks
        clip: true
        spacing: MichiSpacing.xs
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true

        delegate: TrackRow {
            required property int index
            required property var modelData
            width: artistTracksList.width
            numberText: String(index + 1)
            title: modelData.title
            artist: modelData.artist
            album: modelData.album
            durationMs: modelData.durationMs
            quality: modelData.qualityLabel
            playing: playback.currentPath === modelData.path
            favorite: library.favoritePaths.indexOf(modelData.path) !== -1
            showFavorite: true
            showAddToPlaylist: true
            onActivated: library.activate_artist_track(index)
            onFavoriteToggled: library.toggle_favorite(modelData.path)
            onAddToPlaylistRequested: root.addTargetPath = modelData.path
        }
    }
}
