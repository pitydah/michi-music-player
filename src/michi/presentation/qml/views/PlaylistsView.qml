import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../theme"

ColumnLayout {
    id: root
    objectName: "playlistsView"

    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiThemeState.contentGap

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiSpacing.md
        visible: library.selectedPlaylistName === ""

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiTextField {
                id: newPlaylistInput
                Layout.fillWidth: true
                placeholderText: "New playlist…"
                accessibleName: "New playlist name"
                onAccepted: createButton.clicked()
            }
            MichiButton {
                id: createButton
                text: "Create"
                enabled: newPlaylistInput.text.trim().length > 0
                onClicked: {
                    library.create_playlist(newPlaylistInput.text)
                    newPlaylistInput.text = ""
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.playlists.length === 0
            title: "No playlists yet"
            message: "Create a local playlist to organize tracks without changing the library."
        }

        ListView {
            id: playlistList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.playlists.length > 0
            model: library.playlists
            clip: true
            spacing: MichiSpacing.xs
            boundsBehavior: Flickable.StopAtBounds

            delegate: MichiEntityRow {
                required property var modelData
                width: playlistList.width
                iconName: "queue"
                title: modelData.name
                technical: modelData.trackCount + " tracks"
                onActivated: library.select_playlist(modelData.name)
            }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiSpacing.md
        visible: library.selectedPlaylistName !== ""

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiButton {
                text: "Back"
                variant: "ghost"
                onClicked: library.clear_playlist_selection()
            }
            PageHeader {
                Layout.fillWidth: true
                title: library.selectedPlaylistName
                subtitle: library.playlistTrackRows.length + " tracks"
            }
            MichiButton {
                text: "Play"
                iconName: "play"
                enabled: library.playlistTrackRows.length > 0
                onClicked: library.play_selected_playlist()
            }
            MichiButton {
                text: "Delete"
                variant: "ghost"
                onClicked: library.delete_playlist(library.selectedPlaylistName)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiTextField {
                id: renamePlaylistInput
                Layout.fillWidth: true
                placeholderText: "Rename playlist…"
                accessibleName: "New playlist name"
                onAccepted: renameButton.clicked()
            }
            MichiButton {
                id: renameButton
                text: "Rename"
                variant: "secondary"
                enabled: renamePlaylistInput.text.trim().length > 0
                onClicked: {
                    library.rename_playlist(
                        library.selectedPlaylistName, renamePlaylistInput.text
                    )
                    renamePlaylistInput.text = ""
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.playlistTrackRows.length === 0
            title: "Empty playlist"
            message: "Use the add button on a track to place it here."
        }

        ListView {
            id: playlistTracksList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: library.playlistTrackRows.length > 0
            model: library.playlistTrackRows
            clip: true
            spacing: MichiSpacing.xs
            boundsBehavior: Flickable.StopAtBounds

            delegate: RowLayout {
                required property int index
                required property var modelData
                width: playlistTracksList.width
                spacing: MichiSpacing.xs

                TrackRow {
                    Layout.fillWidth: true
                    numberText: String(index + 1)
                    title: modelData.title || modelData.displayName
                    artist: modelData.artist || ""
                    album: modelData.album || ""
                    durationMs: modelData.durationMs || 0
                    quality: modelData.qualityLabel || ""
                    playing: playback.currentPath === modelData.path
                    interactive: false
                }
                MichiIconButton {
                    iconName: "up"
                    accessibleName: "Move track up"
                    enabled: index > 0
                    onClicked: library.move_playlist_track(index, index - 1)
                }
                MichiIconButton {
                    iconName: "down"
                    accessibleName: "Move track down"
                    enabled: index + 1 < library.playlistTrackRows.length
                    onClicked: library.move_playlist_track(index, index + 1)
                }
                MichiIconButton {
                    iconName: "trash"
                    accessibleName: "Remove from playlist"
                    onClicked: library.remove_playlist_track(index)
                }
            }
        }
    }
}
