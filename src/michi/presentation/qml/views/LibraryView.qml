import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {

    property string currentTab: "songs"

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
            }
        }

        PathView {
            id: albumsPath
            objectName: "albumsPathView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: currentTab === "albums" && library.selectedAlbumKey === ""
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
    }
}
