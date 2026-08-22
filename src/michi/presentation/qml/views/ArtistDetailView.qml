import QtQuick
import QtQuick.Controls.Basic
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

    // Elevated glass hero matching AlbumDetailView's weight (was a bare
    // RowLayout that read as unfinished next to the album hero).
    MichiGlassSurface {
        Layout.fillWidth: true
        Layout.preferredHeight: artistHeroContent.implicitHeight + MichiSpacing.xl * 2
        elevation: "elevated"
        contentPadding: MichiSpacing.xl
        accented: true
        accentColor: MichiPalette.auroraBlue
        textured: true

        RowLayout {
            id: artistHeroContent
            anchors.fill: parent
            spacing: MichiSpacing.lg

            Rectangle {
                Layout.preferredWidth: 92
                Layout.preferredHeight: 92
                radius: 46
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: MichiPalette.auroraBlue }
                    GradientStop { position: 0.5; color: MichiPalette.auroraCyan }
                    GradientStop { position: 1; color: MichiPalette.auroraPurple }
                }
                Artwork {
                    anchors.fill: parent
                    anchors.margins: 3
                    radius: width / 2
                    requestedSize: 192
                    sourcePath: library.artistAlbums.length > 0
                        ? library.artistAlbums[0].artworkPath : ""
                    fallbackText: library.artistName
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
        headerPositioning: ListView.InlineHeader

        ScrollBar.vertical: MichiScrollBar { }

        header: TrackTableHeader {
            width: artistTracksList.width
            showArtistColumn: false
            actionColumnWidth: 76
        }

        delegate: TrackRow {
            required property int index
            required property var modelData
            width: artistTracksList.width
            numberText: String(index + 1)
            title: modelData.title
            artist: modelData.artist
            showArtistColumn: false
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
