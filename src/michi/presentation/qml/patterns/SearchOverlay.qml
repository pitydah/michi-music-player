import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Item {
    id: root
    property bool opened: false
    signal closeRequested()
    signal navigationRequested(string routeId)
    visible: opacity > 0
    opacity: opened ? 1 : 0
    enabled: opened
    Keys.onEscapePressed: closeRequested()
    Behavior on opacity { NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outCubic } }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.025, 0.04, 0.72)
        MouseArea { anchors.fill: parent; onClicked: root.closeRequested() }
    }
    MichiGlassSurface {
        elevation: "modal"
        width: Math.min(720, root.width - MichiSpacing.xxl * 2)
        height: Math.min(520, root.height - MichiSpacing.xxl * 2)
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.opened ? MichiSpacing.xxxl : MichiSpacing.xxl
        Behavior on y { NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outCubic } }

        ColumnLayout {
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiSearchField {
                id: searchInput
                Layout.fillWidth: true
                text: library.searchQuery
                placeholderText: "Search tracks, albums, artists and playlists"
                onEdited: query => library.search(query)
                onClearRequested: library.clear_search()
            }
            MichiText {
                visible: library.searchActive
                text: library.searchTotalCount + " results · "
                    + library.searchTrackCount + " tracks · "
                    + library.searchAlbumCount + " albums · "
                    + library.searchArtistCount + " artists"
                role: "technical"
                technical: true
            }
            MichiDivider { Layout.fillWidth: true }
            EmptyState {
                Layout.fillWidth: true; Layout.fillHeight: true
                visible: !library.searchActive || library.searchTotalCount === 0
                title: library.searchActive ? "No results" : "Search your library"
                message: library.searchActive
                    ? "Try a title, artist, album, genre or composer."
                    : "Results are grouped by musical entity and remain fully local."
            }
            MichiScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: library.searchActive && library.searchTotalCount > 0
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.md

                    MichiText { text: "Tracks"; role: "section"; visible: library.searchTrackCount > 0 }
                    Repeater {
                        model: Math.min(6, library.searchTrackCount)
                        delegate: MichiButton {
                            required property int index
                            Layout.fillWidth: true
                            text: library.files[index]
                            variant: "ghost"
                            onClicked: {
                                library.activate(index)
                                root.closeRequested()
                                root.navigationRequested("now_playing")
                            }
                        }
                    }

                    MichiText { text: "Albums"; role: "section"; visible: library.searchAlbumCount > 0 }
                    Repeater {
                        model: Math.min(6, library.searchAlbumCount)
                        delegate: MichiButton {
                            required property int index
                            Layout.fillWidth: true
                            text: library.albums[index].title + " · " + library.albums[index].artist
                            variant: "ghost"
                            onClicked: {
                                library.select_album(library.albums[index].key)
                                root.closeRequested()
                                root.navigationRequested("library")
                            }
                        }
                    }

                    MichiText { text: "Artists"; role: "section"; visible: library.searchArtistCount > 0 }
                    Repeater {
                        model: Math.min(6, library.searchArtistCount)
                        delegate: MichiText {
                            required property int index
                            Layout.fillWidth: true
                            text: library.artists[index].name + " · "
                                + library.artists[index].trackCount + " tracks"
                            role: "secondary"
                        }
                    }

                    MichiText { text: "Genres"; role: "section"; visible: library.searchGenreCount > 0 }
                    Repeater {
                        model: Math.min(6, library.searchGenreCount)
                        delegate: MichiText {
                            required property int index
                            Layout.fillWidth: true
                            text: library.genres[index].name + " · "
                                + library.genres[index].trackCount + " tracks"
                            role: "secondary"
                        }
                    }
                }
            }
        }
        Component.onCompleted: if (root.opened) searchInput.forceInputFocus()
    }
    onOpenedChanged: if (opened) { forceActiveFocus(); searchInput.forceInputFocus() }
}
