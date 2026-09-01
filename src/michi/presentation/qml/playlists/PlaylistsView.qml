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
    property string sortMode: "name" // "name", "name_desc", "tracks", "duration", "pinned", "recent"
    property string displayMode: "grid" // "grid" | "list"
    signal createPlaylistRequested()
    signal openPlaylistRequested(string playlistId)
    signal playPlaylistRequested(string playlistId)
    signal pinPlaylistRequested(string playlistId, bool pinned, string playlistName)
    signal customizeAppearanceRequested(string playlistId)
    signal renamePlaylistRequested(string playlistId, string playlistName)
    signal deletePlaylistRequested(string playlistId, string playlistName)

    function customizeAppearance(row) {
        // R3-06: el panel ÚNICO vive en ContentHost.
        root.customizeAppearanceRequested(row.playlistId)
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


    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        spacing: MichiSpacing.lg

        // Integrated page header: hierarchy and tools share one editorial
        // region without becoming a giant card floating above the page.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 122

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: MichiSemanticColors.contentAmbientBlue }
                    GradientStop { position: 0.58; color: "transparent" }
                    GradientStop { position: 1; color: MichiSemanticColors.contentAmbientPurple }
                }
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: MichiSemanticColors.borderSubtle
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.sm
                anchors.rightMargin: MichiSpacing.sm
                anchors.bottomMargin: MichiSpacing.md
                spacing: MichiSpacing.md

                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: MichiSpacing.xxs
                        MichiText {
                            text: qsTr("Playlists")
                            role: "title"
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

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.md

                    MichiSearchField {
                        id: searchField
                        placeholderText: qsTr("Search playlists…")
                        Layout.minimumWidth: 220
                        Layout.preferredWidth: Math.min(420, Math.max(280, root.width * 0.34))
                        text: root.searchQuery
                        onTextChanged: root.searchQuery = text
                    }

                    MichiComboBox {
                        id: sortCombo
                        Layout.preferredWidth: root.width < 700 ? 132 : 160
                        model: [
                            qsTr("Name A–Z"), qsTr("Name Z–A"),
                            qsTr("Track Count"), qsTr("Duration"),
                            qsTr("Pinned First"), qsTr("Recently Opened")
                        ]
                        onCurrentIndexChanged: {
                            var modes = ["name", "name_desc", "tracks", "duration", "pinned", "recent"]
                            if (currentIndex >= 0 && currentIndex < modes.length)
                                root.sortMode = modes[currentIndex]
                        }
                    }

                    MichiSegmentedControl {
                        compact: true
                        currentValue: root.displayMode
                        accessiblePrefix: qsTr("Playlist view")
                        model: [
                            { value: "grid", label: qsTr("Grid view"), icon: "view-grid" },
                            { value: "list", label: qsTr("List view"), icon: "view-list" }
                        ]
                        onSelected: value => root.displayMode = value
                    }

                    Item { Layout.fillWidth: true }
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
            objectName: "playlistGridView"
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.filteredPlaylists.length > 0 && root.displayMode === "grid"
            clip: true
            // PL-10-FINAL-11: grid responsive REAL — cards ~280–320px en
            // CUALQUIER ancho (hasta ultrawide), sin maxColumns artificial
            // que deje gutters muertos. columnCount deriva del ancho
            // disponible; el conjunto se centra con márgenes simétricos.
            readonly property int targetCellWidth: MichiThemeState.density === "compact" ? 288 : 304
            readonly property int minCellWidth: MichiThemeState.density === "compact" ? 264 : 280
            readonly property int maxCellWidth: MichiThemeState.density === "compact" ? 304 : 320
            readonly property int columnCount: Math.max(
                1, Math.round(width / targetCellWidth))
            readonly property real resolvedCellWidth: Math.min(
                maxCellWidth,
                Math.max(minCellWidth, width / columnCount))
            cellWidth: resolvedCellWidth
            cellHeight: 352
            leftMargin: Math.max(0, (width - columnCount * cellWidth) / 2)
            rightMargin: leftMargin
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
                    width: Math.min(304, parent.width - MichiSpacing.lg)
                    height: 332
                    anchors.top: parent.top
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.topMargin: MichiSpacing.sm
                    selected: playlistCell.current && gridView.activeFocus
                    playlistId: playlistCell.modelData.playlistId
                    playlistName: playlistCell.modelData.name
                    trackCount: playlistCell.modelData.trackCount
                    durationMs: playlistCell.modelData.durationMs || 0
                    customCoverPath: playlistCell.modelData.effectiveCustomCoverPath || ""
                    mosaicArtworkPaths: playlistCell.modelData.mosaicArtworkPaths || []
                    pinned: playlistCell.modelData.pinned
                    onActiveFocusChanged: {
                        if (activeFocus)
                            gridView.currentIndex = playlistCell.index
                    }
                    onOpenRequested: root.openPlaylistRequested(playlistCell.modelData.playlistId)
                    onPlayRequested: root.playPlaylistRequested(playlistCell.modelData.playlistId)
                    onPinToggled: {
                        // R2 P1-12: feedback is shown by ContentHost ONLY
                        // when the pin/unpin was durably committed.
                        root.pinPlaylistRequested(
                            playlistCell.modelData.playlistId,
                            !playlistCell.modelData.pinned,
                            playlistCell.modelData.name)
                    }
                    onCustomizeAppearanceRequested:
                        root.customizeAppearance(playlistCell.modelData)
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
                Accessible.name: modelData.name + ", "
                    + MichiFormat.formatPlaylistSummary(
                        modelData.trackCount, modelData.durationMs)

                contentItem: RowLayout {
                    spacing: MichiSpacing.md
                    anchors.fill: parent
                    anchors.leftMargin: MichiSpacing.md
                    anchors.rightMargin: MichiSpacing.md

                    PlaylistArtwork {
                        Layout.preferredWidth: 40
                        Layout.preferredHeight: 40
                        customCoverPath: modelData.effectiveCustomCoverPath || ""
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
                        Layout.preferredWidth: 14
                        Layout.preferredHeight: 14
                        iconColor: MichiPalette.auroraCyan
                    }

                    MichiText {
                        text: MichiFormat.formatPlaylistSummary(
                            modelData.trackCount, modelData.durationMs)
                        role: "technical"
                        technical: true
                        Layout.preferredWidth: 150
                        color: MichiPalette.textSecondary
                    }

                    MichiIconButton {
                        iconName: "play"
                        accessibleName: qsTr("Play ") + modelData.name
                        onClicked: root.playPlaylistRequested(modelData.playlistId)
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
                        onTriggered: playlists.queue_playlist(modelData.playlistId)
                    }
                    MenuItem {
                        text: modelData.pinned ? qsTr("Unpin") : qsTr("Pin")
                        onTriggered: root.pinPlaylistRequested(modelData.playlistId, !modelData.pinned, modelData.name)
                    }
                    MenuItem {
                        text: qsTr("Customize appearance…")
                        onTriggered: root.customizeAppearance(modelData)
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
