import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

ColumnLayout {
    id: root
    objectName: "playlistsView"

    property string addTargetPath: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: MichiTheme.space8

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiTheme.space8
        visible: library.selectedPlaylistName === ""

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space8

            MichiTextField {
                id: newPlaylistInput
                Layout.fillWidth: true
                placeholderText: "New playlist..."
            }
            MichiButton {
                text: "Create"
                onClicked: {
                    library.create_playlist(newPlaylistInput.text)
                    newPlaylistInput.text = ""
                }
            }
        }

        ListView {
            id: playlistList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: library.playlists
            clip: true
            spacing: MichiTheme.space8
            delegate: RowLayout {
                width: playlistList.width
                height: MichiTheme.controlHeightSmall
                spacing: MichiTheme.space8

                Text {
                    Layout.fillWidth: true
                    text: modelData.name
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textPrimary
                    elide: Text.ElideRight
                }

                Text {
                    text: modelData.trackCount + " tracks"
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.select_playlist(modelData.name)
                }
            }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: MichiTheme.space8
        visible: library.selectedPlaylistName !== ""

        Text {
            text: "← Back"
            font.pixelSize: MichiTheme.fontSizeBody
            color: MichiTheme.textSecondary
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: library.clear_playlist_selection()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space12

            Text {
                Layout.fillWidth: true
                text: library.selectedPlaylistName
                font.pixelSize: MichiTheme.fontSizeTitle
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.textPrimary
                elide: Text.ElideRight
            }

            Text {
                text: "Play"
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.warning
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.play_selected_playlist()
                }
            }

            Text {
                text: "Delete"
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.delete_playlist(library.selectedPlaylistName)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space8

            MichiTextField {
                id: renamePlaylistInput
                Layout.fillWidth: true
                placeholderText: "Rename..."
            }
            Text {
                text: "Rename"
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        library.rename_playlist(
                            library.selectedPlaylistName, renamePlaylistInput.text
                        )
                        renamePlaylistInput.text = ""
                    }
                }
            }
        }

        ListView {
            id: playlistTracksList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: library.playlistTracks
            clip: true
            spacing: MichiTheme.space8
            delegate: RowLayout {
                width: playlistTracksList.width
                height: MichiTheme.controlHeightSmall
                spacing: MichiTheme.space8

                Text {
                    text: "▲"
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: library.move_playlist_track(index, index - 1)
                    }
                }

                Text {
                    text: "▼"
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: library.move_playlist_track(index, index + 1)
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: modelData.displayName
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textPrimary
                    elide: Text.ElideRight
                }

                Text {
                    text: "✕"
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: library.remove_playlist_track(index)
                    }
                }
            }
        }
    }
}
