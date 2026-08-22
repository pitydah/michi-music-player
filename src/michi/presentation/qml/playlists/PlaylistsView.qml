import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
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
    property string sortMode: "name" // "name", "name_desc", "tracks", "duration", "pinned", "recent"
    property string displayMode: "grid" // "grid" | "list"
    property string pendingCoverPlaylistId: ""

    signal createPlaylistRequested()
    signal openPlaylistRequested(string playlistId)
    signal playPlaylistRequested(string playlistId)
    signal pinPlaylistRequested(string playlistId, bool pinned)
    signal renamePlaylistRequested(string playlistId, string playlistName)
    signal deletePlaylistRequested(string playlistId, string playlistName)

    FileDialog {
        id: coverDialog
        title: qsTr("Select Playlist Cover Image")
        nameFilters: ["Image files (*.png *.jpg *.jpeg *.webp)"]
        onAccepted: {
            if (root.pendingCoverPlaylistId) {
                var path = selectedFile.toString()
                playlists.set_custom_cover(root.pendingCoverPlaylistId, path)
                root.pendingCoverPlaylistId = ""
            }
        }
    }

    readonly property var filteredPlaylists: {
        var list = (playlists.playlists || []).slice()
        if (root.searchQuery.trim() !== "") {
            var q = root.searchQuery.trim().toLowerCase()
            list = list.filter(p => p.name.toLowerCase().indexOf(q) !== -1)
        }
        if (root.sortMode === "name") {
            list.sort((a, b) => a.name.localeCompare(b.name))
        } else if (root.sortMode === "name_desc") {
            list.sort((a, b) => b.name.localeCompare(a.name))
        } else if (root.sortMode === "tracks") {
            list.sort((a, b) => b.trackCount - a.trackCount)
        } else if (root.sortMode === "duration") {
            list.sort((a, b) => (b.durationMs || 0) - (a.durationMs || 0))
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
                    text: {
                        var count = playlists.playlists ? playlists.playlists.length : 0
                        return count + " " + (count === 1 ? qsTr("playlist") : qsTr("playlists"))
                    }
                    role: "technical"
                    technical: true
                    color: MichiPalette.textSecondary
                }
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: qsTr("New Playlist")
                iconName: "plus"
                variant: "primary"
                accessibleName: qsTr("Create new playlist")
                onClicked: root.createPlaylistRequested()
            }
        }

        // Toolbar: Search + Sort + View Mode Switcher
        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.md

            MichiSearchField {
                id: searchField
                placeholderText: qsTr("Search playlists…")
                Layout.preferredWidth: Math.min(320, Math.max(220, root.width * 0.35))
                text: root.searchQuery
                onTextChanged: root.searchQuery = text
            }

            MichiComboBox {
                id: sortCombo
                Layout.preferredWidth: 150
                model: [
                    qsTr("Name A–Z"),
                    qsTr("Name Z–A"),
                    qsTr("Track Count"),
                    qsTr("Duration"),
                    qsTr("Pinned First"),
                    qsTr("Recently Opened")
                ]
                onCurrentIndexChanged: {
                    var modes = ["name", "name_desc", "tracks", "duration", "pinned", "recent"]
                    if (currentIndex >= 0 && currentIndex < modes.length)
                        root.sortMode = modes[currentIndex]
                }
            }

            Item { Layout.fillWidth: true }

            RowLayout {
                spacing: MichiSpacing.xxs

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
            keyNavigationEnabled: true
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            Accessible.role: Accessible.List
            Accessible.name: "Playlists in grid view"
            Accessible.description: "Use arrow keys to browse and Enter to open a playlist"

            Keys.onReturnPressed: {
                if (currentIndex >= 0 && currentIndex < root.filteredPlaylists.length)
                    root.openPlaylistRequested(root.filteredPlaylists[currentIndex].playlistId)
            }
            Keys.onEnterPressed: {
                if (currentIndex >= 0 && currentIndex < root.filteredPlaylists.length)
                    root.openPlaylistRequested(root.filteredPlaylists[currentIndex].playlistId)
            }
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Home) {
                    currentIndex = count > 0 ? 0 : -1
                    positionViewAtBeginning()
                    event.accepted = true
                } else if (event.key === Qt.Key_End) {
                    currentIndex = count > 0 ? count - 1 : -1
                    positionViewAtEnd()
                    event.accepted = true
                }
            }

            delegate: Item {
                id: playlistCell
                required property int index
                required property var modelData
                readonly property bool current: GridView.isCurrentItem

                width: gridView.cellWidth
                height: gridView.cellHeight

                PlaylistCard {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.lg / 2
                    selected: playlistCell.current
                    playlistId: playlistCell.modelData.playlistId
                    playlistName: playlistCell.modelData.name
                    trackCount: playlistCell.modelData.trackCount
                    durationMs: playlistCell.modelData.durationMs || 0
                    customCoverPath: playlistCell.modelData.customCoverPath || ""
                    mosaicArtworkPaths: playlistCell.modelData.mosaicArtworkPaths || []
                    pinned: playlistCell.modelData.pinned
                    onActiveFocusChanged: {
                        if (activeFocus)
                            gridView.currentIndex = playlistCell.index
                    }
                    onOpenRequested: root.openPlaylistRequested(playlistCell.modelData.playlistId)
                    onPlayRequested: root.playPlaylistRequested(playlistCell.modelData.playlistId)
                    onPinToggled: root.pinPlaylistRequested(playlistCell.modelData.playlistId, !playlistCell.modelData.pinned)
                    onChangeCoverRequested: {
                        root.pendingCoverPlaylistId = playlistCell.modelData.playlistId
                        coverDialog.open()
                    }
                    onRenameRequested: root.renamePlaylistRequested(
                        playlistCell.modelData.playlistId, playlistCell.modelData.name)
                    onDeleteRequested: root.deletePlaylistRequested(
                        playlistCell.modelData.playlistId, playlistCell.modelData.name)
                }
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

                    MichiIconButton {
                        iconName: "more"
                        accessibleName: qsTr("More options for ") + modelData.name
                        onClicked: listRowMenu.popup()
                    }
                }

                MichiMenu {
                    id: listRowMenu
                    MenuItem {
                        text: qsTr("Open")
                        onTriggered: root.openPlaylistRequested(modelData.playlistId)
                    }
                    MenuItem {
                        text: qsTr("Play Now")
                        onTriggered: root.playPlaylistRequested(modelData.playlistId)
                    }
                    MenuItem {
                        text: qsTr("Add to Queue")
                        onTriggered: playlists.enqueue_playlist(modelData.playlistId)
                    }
                    MenuItem {
                        text: modelData.pinned ? qsTr("Unpin") : qsTr("Pin")
                        onTriggered: root.pinPlaylistRequested(modelData.playlistId, !modelData.pinned)
                    }
                    MenuItem {
                        text: qsTr("Change Cover…")
                        onTriggered: {
                            root.pendingCoverPlaylistId = modelData.playlistId
                            coverDialog.open()
                        }
                    }
                    MenuItem {
                        text: qsTr("Use Automatic Mosaic")
                        visible: (modelData.customCoverPath || "") !== ""
                        onTriggered: playlists.remove_custom_cover(modelData.playlistId)
                    }
                    MenuItem {
                        text: qsTr("Rename…")
                        onTriggered: root.renamePlaylistRequested(modelData.playlistId, modelData.name)
                    }
                    MenuItem {
                        text: qsTr("Delete…")
                        onTriggered: root.deletePlaylistRequested(modelData.playlistId, modelData.name)
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
