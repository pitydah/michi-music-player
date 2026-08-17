import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {

    property string currentTab: "songs"
    property string albumMode: "grid"
    property string addTargetPath: ""
    readonly property var heroAlbum: library.albums.length > 0 ? library.albums[0] : null

    function formatDuration(ms) {
        if (ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space8

        Text {
            text: "Library" + (library.fileCount > 0 ? " (" + library.fileCount + ")" : "")
            font.pixelSize: MichiTheme.fontSizeBodyLarge
            font.weight: MichiTheme.fontWeightBold
            color: MichiTheme.textSecondary
        }

        RowLayout {
            Layout.fillWidth: true; spacing: MichiTheme.space6
            MichiTextField {
                id: dirInput; Layout.fillWidth: true
                text: library.currentDir
                placeholderText: "Music directory..."
            }
            MichiButton {
                text: "Scan"
                enabled: dirInput.text.length > 0 || library.currentDir.length > 0
                onClicked: {
                    var d = dirInput.text.length > 0 ? dirInput.text : library.currentDir
                    library.scan(d)
                }
            }
        }

        MichiTextField {
            id: searchInput; Layout.fillWidth: true
            text: library.searchQuery
            placeholderText: "Search..."
            onTextEdited: library.search(text)
        }

        Text {
            visible: library.hasDiagnostic
            text: library.diagnosticMessage
            color: MichiTheme.warning
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space12

            Text {
                text: "Songs"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "songs" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "songs" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "songs"
                }
            }

            Text {
                text: "Albums"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "albums" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "albums" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "albums"
                }
            }

            Text {
                text: "Artists"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "artists" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "artists" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "artists"
                }
            }

            Text {
                text: "Genres"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "genres" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "genres" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "genres"
                }
            }

            Text {
                text: "Folders"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "folders" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "folders" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "folders"
                }
            }

            Text {
                text: "Favorites"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "favorites" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "favorites" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "favorites"
                }
            }

            Text {
                text: "History"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "history" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "history" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "history"
                }
            }

            Text {
                text: "Recently Added"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "recently" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "recently" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "recently"
                }
            }

            Text {
                text: "Playlists"
                font.pixelSize: MichiTheme.fontSizeBody
                font.weight: currentTab === "playlists" ? MichiTheme.fontWeightBold : MichiTheme.fontWeightNormal
                color: currentTab === "playlists" ? MichiTheme.warning : MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: currentTab = "playlists"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space12
            visible: addTargetPath !== ""

            Text {
                text: "Add to:"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
            }

            Repeater {
                model: library.playlists
                delegate: Text {
                    text: modelData.name
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.warning
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            library.add_to_playlist(modelData.name, addTargetPath)
                            addTargetPath = ""
                        }
                    }
                }
            }

            Text {
                text: "✕"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: addTargetPath = ""
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.space12
            visible: currentTab === "albums" && library.selectedAlbumKey === ""

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

        ColumnLayout {
            visible: library.selectedAlbumKey !== ""
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: MichiTheme.space8

            Text {
                text: "← Back"
                font.pixelSize: MichiTheme.fontSizeBody
                color: MichiTheme.textSecondary
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.clear_album_selection()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.space12

                Image {
                    source: "file://" + library.albumArtwork
                    visible: library.albumArtwork !== ""
                    Layout.preferredWidth: 120
                    Layout.preferredHeight: 120
                    fillMode: Image.PreserveAspectFit
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: MichiTheme.space4

                    Text {
                        Layout.fillWidth: true
                        text: library.albumTitle
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textPrimary
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: library.albumArtist
                        font.pixelSize: MichiTheme.fontSizeBody
                        color: MichiTheme.textSecondary
                        elide: Text.ElideRight
                    }
                }
            }

            ListView {
                id: albumTracksList; Layout.fillWidth: true; Layout.fillHeight: true
                model: library.albumTracks; clip: true
                delegate: RowLayout {
                    width: albumTracksList.width
                    height: MichiTheme.controlHeightSmall
                    spacing: MichiTheme.space8

                    Text {
                        Layout.fillWidth: true
                        text: modelData.displayName
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textPrimary
                        elide: Text.ElideRight
                    }

                    Text {
                        text: modelData.artist
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textSecondary
                        elide: Text.ElideRight
                    }

                    Text {
                        text: formatDuration(modelData.durationMs)
                        font.pixelSize: MichiTheme.fontSizeCaption
                        color: MichiTheme.textSecondary
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: library.activate_album_track(index)
                    }

                    Text {
                        text: library.favoritePaths.indexOf(modelData.path) !== -1 ? "★" : "☆"
                        color: MichiTheme.warning
                        font.pixelSize: MichiTheme.fontSizeCaption
                        Layout.rightMargin: MichiTheme.space8
                    }
                    MouseArea {
                        width: 24
                        height: parent.height
                        cursorShape: Qt.PointingHandCursor
                        Layout.rightMargin: MichiTheme.space8
                        onClicked: library.toggle_favorite(modelData.path)
                    }

                    Text {
                        text: "＋"
                        color: MichiTheme.warning
                        font.pixelSize: MichiTheme.fontSizeCaption
                        Layout.rightMargin: MichiTheme.space8
                    }
                    MouseArea {
                        width: 24
                        height: parent.height
                        cursorShape: Qt.PointingHandCursor
                        Layout.rightMargin: MichiTheme.space8
                        onClicked: addTargetPath = modelData.path
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: MichiTheme.space8
            visible: currentTab === "playlists" && library.selectedPlaylistName === ""

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
                id: playlistList; Layout.fillWidth: true; Layout.fillHeight: true
                model: library.playlists; clip: true
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
            visible: currentTab === "playlists" && library.selectedPlaylistName !== ""

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
                id: playlistTracksList; Layout.fillWidth: true; Layout.fillHeight: true
                model: library.playlistTracks; clip: true
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

        ListView {
            id: libList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "songs" && library.selectedAlbumKey === ""
            model: library.files; clip: true
            delegate: Rectangle {
                width: libList.width
                height: MichiTheme.controlHeightSmall
                color: mouseArea.containsMouse ? MichiTheme.surfaceHover : "transparent"
                radius: MichiTheme.radiusSmall
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left; anchors.leftMargin: MichiTheme.space8
                    text: modelData; color: MichiTheme.textSecondary
                    font.pixelSize: MichiTheme.fontSizeCaption
                    elide: Text.ElideRight; width: parent.width - MichiTheme.space16
                }
                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.activate(index)
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: MichiTheme.space8
                    text: library.favoritePaths.indexOf(library.songPaths[index]) !== -1 ? "★" : "☆"
                    color: MichiTheme.warning
                    font.pixelSize: MichiTheme.fontSizeCaption
                }
                MouseArea {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    height: parent.height
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.toggle_favorite(library.songPaths[index])
                }

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: MichiTheme.space8 + 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: "＋"
                    color: MichiTheme.warning
                    font.pixelSize: MichiTheme.fontSizeCaption
                }
                MouseArea {
                    anchors.right: parent.right
                    anchors.rightMargin: MichiTheme.space8 + 24
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    height: parent.height
                    cursorShape: Qt.PointingHandCursor
                    onClicked: addTargetPath = library.songPaths[index]
                }
            }
        }

        PathView {
            id: albumsPath
            objectName: "albumCoverView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "cover"
            model: library.albums
            clip: true
            pathItemCount: 3
            preferredHighlightBegin: 0.5
            preferredHighlightEnd: 0.5
            path: Path {
                startX: 0
                startY: albumsPath.height / 2
                PathLine { x: albumsPath.width / 2; y: albumsPath.height / 2 }
                PathLine { x: albumsPath.width; y: albumsPath.height / 2 }
            }
            delegate: Item {
                width: 180
                height: 220

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radiusSmall
                    color: PathView.isCurrentItem ? MichiTheme.surfaceSelected : MichiTheme.surfaceHover
                }

                Image {
                    anchors.fill: parent
                    anchors.margins: 6
                    source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                    fillMode: Image.PreserveAspectFit
                    visible: modelData.hasArtwork
                }

                Text {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 8
                    text: modelData.title
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: PathView.isCurrentItem ? MichiTheme.textPrimary : MichiTheme.textSecondary
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        albumsPath.currentIndex = index
                        library.select_album(modelData.key)
                    }
                }

                scale: PathView.isCurrentItem ? 1.0 : 0.85
                z: PathView.isCurrentItem ? 2 : 1
                opacity: PathView.isCurrentItem ? 1.0 : 0.6
            }
        }

        GridView {
            id: albumGrid
            objectName: "albumGridView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "grid"
            model: library.albums
            cellWidth: 150
            cellHeight: 190
            clip: true
            delegate: Item {
                width: 150
                height: 190

                Rectangle {
                    anchors.fill: parent
                    radius: MichiTheme.radiusSmall
                    color: MichiTheme.surfaceHover
                    visible: !modelData.hasArtwork

                    Text {
                        anchors.centerIn: parent
                        text: modelData.title.length > 0 ? modelData.title.charAt(0).toUpperCase() : "?"
                        font.pixelSize: MichiTheme.fontSizeTitle
                        font.weight: MichiTheme.fontWeightBold
                        color: MichiTheme.textSecondary
                    }
                }

                Image {
                    anchors.fill: parent
                    anchors.margins: 6
                    source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                    visible: modelData.hasArtwork
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 6
                    text: modelData.title
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textPrimary
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.select_album(modelData.key)
                }
            }
        }

        GridView {
            id: albumVinyl
            objectName: "albumVinylView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "vinyl"
            model: library.albums
            cellWidth: 140
            cellHeight: 170
            clip: true
            delegate: Item {
                width: 140
                height: 170

                Rectangle {
                    id: vinylDisc
                    width: 100
                    height: 100
                    radius: 50
                    color: MichiTheme.surfaceSelected
                    border.width: 1
                    border.color: MichiTheme.borderSubtle
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top

                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 9000
                        loops: Animation.Infinite
                        running: true
                    }

                    Rectangle {
                        width: 56
                        height: 56
                        radius: 28
                        color: MichiTheme.surfaceHover
                        clip: true
                        anchors.centerIn: parent

                        Image {
                            anchors.fill: parent
                            source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                            visible: modelData.hasArtwork
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                }

                Text {
                    anchors.top: vinylDisc.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    anchors.topMargin: MichiTheme.space8
                    text: modelData.title
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: library.select_album(modelData.key)
                }
            }
        }

        ListView {
            id: albumTimeline
            objectName: "albumTimelineView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "timeline"
            model: library.timelineAlbums
            clip: true
            section.property: "decade"
            section.criteria: ViewSection.FullString
            section.delegate: Text {
                width: albumTimeline.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: section
                font.pixelSize: MichiTheme.fontSizeCaption
                font.weight: MichiTheme.fontWeightBold
                color: MichiTheme.warning
                padding: MichiTheme.space8
            }
            delegate: RowLayout {
                width: albumTimeline.width
                height: MichiTheme.controlHeightSmall
                spacing: MichiTheme.space8

                Image {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                    visible: modelData.hasArtwork
                    fillMode: Image.PreserveAspectFit
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

        ColumnLayout {
            id: albumMagazine
            objectName: "albumMagazineView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "magazine"
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

                Image {
                    anchors.fill: parent
                    source: heroAlbum !== null && heroAlbum.hasArtwork ? "file://" + heroAlbum.artworkPath : ""
                    visible: heroAlbum !== null && heroAlbum.hasArtwork
                    fillMode: Image.PreserveAspectFit
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

                    Image {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                        visible: modelData.hasArtwork
                        fillMode: Image.PreserveAspectFit
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

        ListView {
            id: albumList
            objectName: "albumListView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === "" && albumMode === "list"
            model: library.albums
            clip: true
            spacing: MichiTheme.space8
            delegate: RowLayout {
                width: albumList.width
                height: MichiTheme.controlHeightSmall
                spacing: MichiTheme.space8

                Image {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    source: modelData.hasArtwork ? "file://" + modelData.artworkPath : ""
                    visible: modelData.hasArtwork
                    fillMode: Image.PreserveAspectFit
                }

                Text {
                    Layout.fillWidth: true
                    text: modelData.title
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textPrimary
                    elide: Text.ElideRight
                }

                Text {
                    text: modelData.artist
                    font.pixelSize: MichiTheme.fontSizeCaption
                    color: MichiTheme.textSecondary
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
                    onClicked: library.select_album(modelData.key)
                }
            }
        }

        ListView {
            id: artistsList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "artists" && library.selectedAlbumKey === ""
            model: library.artists; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: artistsList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.name + " · " + modelData.trackCount + " tracks · " + modelData.albumCount + " albums"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }

        ListView {
            id: genresList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "genres" && library.selectedAlbumKey === ""
            model: library.genres; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: genresList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.name + " · " + modelData.trackCount + " tracks"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }

        ListView {
            id: foldersList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "folders" && library.selectedAlbumKey === ""
            model: library.folders; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: foldersList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.path + " · " + modelData.trackCount + " tracks"
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }

        ListView {
            id: favoritesList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "favorites" && library.selectedAlbumKey === ""
            model: library.favoriteRows; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: favoritesList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.displayName
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }

        ListView {
            id: historyList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "history" && library.selectedAlbumKey === ""
            model: library.historyRows; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: historyList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.displayName
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }

        ListView {
            id: recentList; Layout.fillWidth: true; Layout.fillHeight: true
            visible: currentTab === "recently" && library.selectedAlbumKey === ""
            model: library.recentlyAddedRows; clip: true
            spacing: MichiTheme.space8
            delegate: Text {
                width: recentList.width
                height: MichiTheme.controlHeightSmall
                verticalAlignment: Text.AlignVCenter
                text: modelData.displayName
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                elide: Text.ElideRight
            }
        }
    }
}
