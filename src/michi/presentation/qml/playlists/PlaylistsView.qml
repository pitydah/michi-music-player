import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../patterns"
import "../primitives"
import "../theme"

// PlaylistsView — All Playlists. Responsive card grid with search, sort,
// primary Create action, and real artwork mosaic cards.
Item {
    id: root

    objectName: "playlistsView"
    property string searchQuery: ""
    property string sortMode: "name" // "name", "tracks", "recent", "pinned"
    property string displayMode: "grid" // "grid" | "list"

    signal createPlaylistRequested()
    signal openPlaylistRequested(string playlistId)
    signal playPlaylistRequested(string playlistId)
    signal pinPlaylistRequested(string playlistId, bool pinned)
    signal renamePlaylistRequested(string playlistId, string playlistName)
    signal deletePlaylistRequested(string playlistId, string playlistName)

    readonly property var filteredPlaylists: {
        var list = (playlists.playlists || []).slice()
        if (root.searchQuery.trim() !== "") {
            var q = root.searchQuery.trim().toLowerCase()
            list = list.filter(p => p.name.toLowerCase().indexOf(q) !== -1)
        }
        if (root.sortMode === "name") {
            list.sort((a, b) => a.name.localeCompare(b.name))
        } else if (root.sortMode === "tracks") {
            list.sort((a, b) => b.trackCount - a.trackCount)
        } else if (root.sortMode === "pinned") {
            list.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0))
        } else if (root.sortMode === "recent") {
            list.sort((a, b) => {
                var ra = a.recentRank >= 0 ? a.recentRank : 9999
                var rb = b.recentRank >= 0 ? b.recentRank : 9999
                return ra - rb
            })
        }
        return list
    }

    function formatTime(ms) {
        if (!ms || ms <= 0) return ""
        var totalSeconds = Math.round(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        // Header Strip
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md

            ColumnLayout {
                spacing: 2
                MichiText {
                    text: qsTr("Playlists")
                    role: "section"
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    text: (playlists.playlists ? playlists.playlists.length : 0) + " playlists"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
            }

            Item { Layout.preferredWidth: MichiSpacing.md }

            MichiSearchField {
                id: searchInput
                Layout.preferredWidth: 240
                Layout.preferredHeight: 36
                placeholderText: qsTr("Filter playlists…")
                text: root.searchQuery
                onEdited: query => root.searchQuery = query
                onClearRequested: root.searchQuery = ""
            }

            MichiComboBox {
                id: sortBox
                Layout.preferredWidth: 150
                Layout.preferredHeight: 36
                model: ["Name", "Track count", "Pinned first", "Recently played"]
                currentIndex: 0
                onActivated: {
                    var modes = ["name", "tracks", "pinned", "recent"]
                    root.sortMode = modes[currentIndex]
                }
            }

            RowLayout {
                spacing: 2
                MichiIconButton {
                    iconName: "view-grid"
                    selected: root.displayMode === "grid"
                    accessibleName: qsTr("Grid view")
                    onClicked: root.displayMode = "grid"
                }
                MichiIconButton {
                    iconName: "view-list"
                    selected: root.displayMode === "list"
                    accessibleName: qsTr("List view")
                    onClicked: root.displayMode = "list"
                }
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("New Playlist")
                variant: "primary"
                iconName: "plus"
                accessibleName: qsTr("Create playlist")
                onClicked: root.createPlaylistRequested()
            }
        }

        // Empty state
        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !playlists.playlists || playlists.playlists.length === 0
            title: qsTr("No playlists yet")
            message: qsTr("Create a playlist to collect tracks from your library.")
            actionText: qsTr("Create Playlist")
            iconName: "playlist"
            onActionRequested: root.createPlaylistRequested()
        }

        // Filter empty state
        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: playlists.playlists && playlists.playlists.length > 0 && root.filteredPlaylists.length === 0
            title: qsTr("No matching playlists")
            message: qsTr("Try adjusting your filter query.")
            iconName: "playlist"
        }

        // Card grid mode
        GridView {
            id: gridView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.filteredPlaylists.length > 0 && root.displayMode === "grid"
            clip: true
            cellWidth: Math.max(220, (root.width - MichiSpacing.xl * 2) / Math.max(1, Math.floor((root.width - MichiSpacing.xl) / 240)))
            cellHeight: 260
            model: root.filteredPlaylists
            delegate: PlaylistCard {
                width: gridView.cellWidth - MichiSpacing.lg
                height: gridView.cellHeight - MichiSpacing.lg
                playlistId: modelData.playlistId
                playlistName: modelData.name
                trackCount: modelData.trackCount
                durationMs: modelData.durationMs || 0
                customCoverPath: modelData.customCoverPath || ""
                mosaicArtworkPaths: modelData.mosaicArtworkPaths || []
                pinned: modelData.pinned
                onOpenRequested: root.openPlaylistRequested(modelData.playlistId)
                onPlayRequested: root.playPlaylistRequested(modelData.playlistId)
                onPinToggled: root.pinPlaylistRequested(modelData.playlistId, !modelData.pinned)
                onRenameRequested: root.renamePlaylistRequested(
                    modelData.playlistId, modelData.name)
                onDeleteRequested: root.deletePlaylistRequested(
                    modelData.playlistId, modelData.name)
            }
        }

        // Table list mode
        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.filteredPlaylists.length > 0 && root.displayMode === "list"
            clip: true
            spacing: MichiSpacing.xs
            model: root.filteredPlaylists
            delegate: ItemDelegate {
                id: listRow
                width: listView.width
                height: 52
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.ListItem
                Accessible.name: modelData.name + ", " + modelData.trackCount + " tracks"

                contentItem: RowLayout {
                    spacing: MichiSpacing.md
                    anchors.fill: parent
                    anchors.leftMargin: MichiSpacing.md
                    anchors.rightMargin: MichiSpacing.md

                    PlaylistArtwork {
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        customCoverPath: modelData.customCoverPath || ""
                        mosaicArtworkPaths: modelData.mosaicArtworkPaths || []
                        fallbackText: modelData.name
                        radius: MichiRadius.sm
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        MichiText {
                            text: modelData.name
                            role: "secondary"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            color: MichiPalette.textPrimary
                        }
                    }

                    MichiIcon {
                        visible: modelData.pinned
                        name: "pin"
                        width: 14
                        height: 14
                        iconColor: MichiPalette.auroraCyan
                    }

                    MichiText {
                        text: modelData.trackCount + (modelData.trackCount === 1 ? " track" : " tracks")
                        role: "technical"
                        technical: true
                        Layout.preferredWidth: 90
                        color: MichiPalette.textSecondary
                    }

                    MichiText {
                        text: root.formatTime(modelData.durationMs)
                        role: "technical"
                        technical: true
                        Layout.preferredWidth: 70
                        horizontalAlignment: Text.AlignRight
                        color: MichiPalette.textMuted
                    }

                    MichiIconButton {
                        iconName: "play"
                        accessibleName: qsTr("Play ") + modelData.name
                        onClicked: root.playPlaylistRequested(modelData.playlistId)
                    }

                    MichiIconButton {
                        iconName: modelData.pinned ? "pin" : "circle"
                        accessibleName: modelData.pinned
                            ? qsTr("Unpin ") + modelData.name
                            : qsTr("Pin ") + modelData.name
                        onClicked: root.pinPlaylistRequested(modelData.playlistId, !modelData.pinned)
                    }
                }

                background: Rectangle {
                    radius: MichiRadius.md
                    color: listRow.hovered || listRow.visualFocus
                        ? MichiSemanticColors.surfaceHover : "transparent"
                    border.width: 1
                    border.color: listRow.visualFocus
                        ? MichiPalette.auroraCyan : "transparent"
                    Behavior on color {
                        enabled: !MichiAccessibility.reducedMotion
                        ColorAnimation { duration: MichiMotion.micro }
                    }
                }

                onClicked: root.openPlaylistRequested(modelData.playlistId)
            }
        }
    }
}
