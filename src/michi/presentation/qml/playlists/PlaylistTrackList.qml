import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// PlaylistTrackList — dense editorial track table. One continuous surface
// with the PlaylistHero scrolling away on top; rows are quiet, 50px,
// border-bottom only; hover/selected/playing are distinct states.
// The playlist is a persistent collection — selecting and playing a track
// never requires queue operations (see playlists.play_track).
Item {
    id: root

    property var rows: []
    // R3-07: selección visual por PATH estable — el índice es una posición
    // y no sobrevive reorders; el path sí. Playback sigue usando index.
    property string selectedTrackPath: ""
    // PL-FINAL-14/15: selection mode (checkboxes, sin playback) y reorder
    // gated — con un filtro de búsqueda activo el drag reorder se
    // DESHABILITA (un índice filtrado nunca debe reordenar la playlist).
    property bool selectionMode: false
    property bool reorderEnabled: true
    // PL-FINAL-A01: selección por PATH. Esta es todavía una proyección UI;
    // la membership durable permanece TrackId-first en el Bridge/Service.
    property var checkedPaths: []
    // The header must be a COMPONENT: ListView.header assigns to its
    // internal QQmlComponent slot — passing a pre-instantiated Item (typed
    // var or Item) fails with "Unable to assign ... to QQmlComponent" and
    // the header silently never appears. The page instantiates the
    // PlaylistHero inside a Component and wires its signals via
    // Connections on headerItem.
    property Component heroComponent: null
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showFormatColumn: false
    property bool narrow: false
    readonly property real contentY: trackList.contentY

    signal playTrackRequested(int index)
    signal trackSelected(string path)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)
    signal selectionToggleRequested(string path, bool shiftHeld)

    function _syncSelectedIndex() {
        if (root.selectedTrackPath.length === 0)
            return
        for (var i = 0; i < root.rows.length; ++i) {
            if (root.rows[i].path === root.selectedTrackPath) {
                trackList.currentIndex = i
                return
            }
        }
        trackList.currentIndex = -1
    }
    onRowsChanged: root._syncSelectedIndex()

    function resetForPlaylist() {
        trackList.positionViewAtBeginning()
        trackList.currentIndex = root.rows.length > 0 ? 0 : -1
    }

    implicitHeight: 420
    clip: true

    ListView {
        id: trackList
        objectName: "playlistTrackList"
        anchors.fill: parent
        model: root.rows
        clip: true
        spacing: 0
        reuseItems: true
        cacheBuffer: 400
        boundsBehavior: Flickable.StopAtBounds
        keyNavigationEnabled: true
        keyNavigationWraps: false
        activeFocusOnTab: true
        focus: true
        header: root.heroComponent
        headerPositioning: ListView.InlineHeader
        Accessible.role: Accessible.List
        Accessible.name: qsTr("Playlist tracks")
        ScrollBar.vertical: MichiScrollBar { }

        Keys.onReturnPressed: {
            if (currentIndex >= 0 && currentIndex < root.rows.length
                    && root.rows[currentIndex].canonicalIndex !== undefined
                    && root.rows[currentIndex].available !== false)
                root.playTrackRequested(root.rows[currentIndex].canonicalIndex)
        }
        Keys.onEnterPressed: {
            if (currentIndex >= 0 && currentIndex < root.rows.length
                    && root.rows[currentIndex].canonicalIndex !== undefined
                    && root.rows[currentIndex].available !== false)
                root.playTrackRequested(root.rows[currentIndex].canonicalIndex)
        }

        DropArea {
            anchors.fill: parent
            keys: ["application/x-michi-playlist-index"]
            enabled: root.reorderEnabled && !root.selectionMode

            onPositionChanged: drag => {
                var to = trackList.indexAt(drag.x, drag.y)
                var item = to >= 0 ? trackList.itemAtIndex(to) : null
                if (!item) {
                    insertLine.visible = false
                    return
                }
                insertLine.visible = true
                insertLine.y = drag.y > item.y + item.height / 2
                    ? item.y + item.height : item.y
            }
            onExited: insertLine.visible = false
            onDropped: drag => {
                insertLine.visible = false
                var from = parseInt(
                    drag.mimeData["application/x-michi-playlist-index"])
                var to = trackList.indexAt(drag.x, drag.y)
                if (from >= 0 && to >= 0 && from !== to)
                    root.moveTrackRequested(from, to)
                drag.accept(Qt.MoveAction)
            }
        }

        Rectangle {
            id: insertLine
            visible: false
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: MichiSpacing.md
            anchors.rightMargin: MichiSpacing.md
            height: 2
            radius: 1
            color: MichiPalette.auroraCyan
            z: 10
        }

        delegate: ItemDelegate {
            id: trackItem
            required property int index
            required property var modelData
            width: trackList.width
            height: 50
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.ListItem
            Accessible.name: modelData.title + " — " + modelData.artist

            readonly property int canonicalIndex:
                modelData.canonicalIndex !== undefined
                    ? modelData.canonicalIndex : index
            readonly property bool isPlaying: typeof playback !== "undefined"
                && playback && modelData.path
                && playback.currentPath === modelData.path
            readonly property bool isSelected:
                root.selectedTrackPath === modelData.path
            readonly property bool unavailable: modelData.available === false
                || modelData.unavailableReason !== undefined
                && modelData.unavailableReason !== ""
            readonly property bool canInteract: !trackItem.unavailable
            readonly property bool hasStableTrackId:
                modelData.trackId !== undefined && String(modelData.trackId).length > 0
            readonly property bool isFavorite: {
                // M9-R3 CONVERGENCE SEAL: id canónico, proyección legacy
                // (legacy-path::<path>) o path-only — los tres chequean.
                if (typeof library === "undefined" || !library)
                    return false
                if (trackItem.hasStableTrackId
                        && library.favoriteTrackIds.indexOf(
                            String(modelData.trackId)) !== -1)
                    return true
                if (modelData.path) {
                    if (library.favoriteTrackIds.indexOf(
                            "legacy-path::" + modelData.path) !== -1)
                        return true
                    if (!trackItem.hasStableTrackId
                            && library.favoritePaths.indexOf(
                                modelData.path) !== -1)
                        return true
                }
                return false
            }
            readonly property bool actionsVisible:
                trackItem.hovered || trackItem.visualFocus
                || favoriteButton.activeFocus || moreButton.activeFocus
                || trackMenu.visible

            function selectExactTarget() {
                root.trackSelected(modelData.path)
                trackList.currentIndex = trackItem.index
                trackItem.forceActiveFocus()
            }

            function toggleFavorite() {
                if (typeof library === "undefined" || !library)
                    return
                if (trackItem.hasStableTrackId)
                    library.toggle_favorite_by_id(String(modelData.trackId))
                else
                    library.toggle_favorite(modelData.path)
            }

            contentItem: Item {
                anchors.fill: parent

                MouseArea {
                    id: rowSurface
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    cursorShape: Qt.PointingHandCursor
                    onClicked: mouse => {
                        // M9-R3 CONTEXTUAL RECOVERY: right-click targets the
                        // exact row and NEVER triggers playback/selection-mode
                        // toggling as a side effect.
                        if (mouse.button === Qt.RightButton) {
                            trackItem.selectExactTarget()
                            trackMenu.popup()
                            return
                        }
                        if (root.selectionMode) {
                            root.selectionToggleRequested(
                                modelData.path,
                                (mouse.modifiers & Qt.ShiftModifier) !== 0)
                            return
                        }
                        root.trackSelected(modelData.path)
                        if (trackItem.canInteract)
                            root.playTrackRequested(trackItem.canonicalIndex)
                    }
                }

                RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.md
                anchors.rightMargin: MichiSpacing.sm
                spacing: MichiSpacing.md

                Item {
                    Layout.preferredWidth: root.selectionMode ? 40 : 36
                    Layout.preferredHeight: 40

                    CheckBox {
                        visible: root.selectionMode
                        anchors.centerIn: parent
                        checked: root.checkedPaths.indexOf(modelData.path) !== -1
                        Accessible.name: qsTr("Select ") + modelData.title
                        onToggled: root.selectionToggleRequested(
                            modelData.path, false)
                    }

                    Drag.active: root.reorderEnabled && dragHandler.active
                    Drag.source: root.reorderEnabled ? trackItem : null
                    Drag.supportedActions: Qt.MoveAction
                    Drag.mimeData: { "application/x-michi-playlist-index": index }
                    Drag.hotSpot.x: width / 2
                    Drag.hotSpot.y: height / 2

                    DragHandler {
                        id: dragHandler
                        enabled: root.reorderEnabled && !root.selectionMode
                        acceptedButtons: Qt.LeftButton
                        cursorShape: Qt.OpenHandCursor
                        onActiveChanged: trackItem.opacity = active ? 0.45 : 1
                    }

                    MichiText {
                        anchors.centerIn: parent
                        visible: !trackItem.isPlaying && !root.selectionMode
                        text: index + 1
                        role: "technical"
                        technical: true
                        color: trackItem.isSelected
                            ? MichiPalette.textSecondary : MichiPalette.textMuted
                        horizontalAlignment: Text.AlignRight
                    }
                    MichiPlayingIndicator {
                        anchors.centerIn: parent
                        visible: trackItem.isPlaying
                        width: 12
                        height: 12
                        playing: trackItem.isPlaying
                    }
                }

                Artwork {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    sourcePath: modelData.artworkPath || ""
                    fallbackText: modelData.title || modelData.displayName || "T"
                    radius: 4
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.preferredWidth: root.narrow ? 0 : trackList.width * 0.36
                    Layout.minimumWidth: 120
                    spacing: 0
                    Layout.alignment: Qt.AlignVCenter
                    MichiText {
                        Layout.fillWidth: true
                        text: modelData.title
                        role: "body"
                        font.weight: Font.Medium
                        color: trackItem.isPlaying
                            ? MichiPalette.auroraCyan : MichiPalette.textPrimary
                        elide: Text.ElideRight
                    }
                    MichiText {
                        Layout.fillWidth: true
                        visible: root.narrow && modelData.artist !== ""
                        text: modelData.artist
                        role: "secondary"
                        color: MichiPalette.textSecondary
                        opacity: 0.65
                        elide: Text.ElideRight
                    }
                }

                MichiText {
                    visible: root.showArtistColumn && !root.narrow
                    Layout.preferredWidth: trackList.width * 0.2
                    Layout.minimumWidth: 90
                    Layout.maximumWidth: 240
                    text: modelData.artist || "—"
                    role: "technical"
                    color: MichiPalette.textSecondary
                    opacity: 0.65
                    elide: Text.ElideRight
                }

                MichiText {
                    visible: root.showAlbumColumn
                    Layout.preferredWidth: trackList.width * 0.2
                    Layout.minimumWidth: 90
                    Layout.maximumWidth: 240
                    text: modelData.album || "—"
                    role: "technical"
                    color: MichiPalette.textSecondary
                    opacity: 0.6
                    elide: Text.ElideRight
                }

                MichiText {
                    visible: root.showFormatColumn
                    Layout.preferredWidth: Math.max(96, trackList.width * 0.13)
                    Layout.minimumWidth: 96
                    Layout.maximumWidth: 200
                    text: (modelData.qualityLabel && modelData.qualityLabel !== "")
                        ? modelData.qualityLabel : ""
                    role: "technical"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                }

                MichiText {
                    visible: trackItem.unavailable
                    text: qsTr("Unavailable")
                    role: "technical"
                    color: MichiPalette.textSecondary
                    opacity: 0.55
                }

                MichiText {
                    Layout.preferredWidth: 54
                    text: modelData.durationMs > 0 ? MichiFormat.formatDuration(modelData.durationMs) : ""
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    horizontalAlignment: Text.AlignRight
                }

                MichiIconButton {
                    id: favoriteButton
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "heart"
                    accessibleName: trackItem.isFavorite
                        ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    selected: trackItem.isFavorite
                    opacity: actionsVisible ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                    onClicked: trackItem.toggleFavorite()
                }
                MichiIconButton {
                    id: moreButton
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "more"
                    accessibleName: qsTr("More options for ") + modelData.title
                    opacity: actionsVisible ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                    onClicked: {
                        trackItem.selectExactTarget()
                        trackMenu.popup()
                    }
                }
                }
            }

            onActiveFocusChanged: {
                if (activeFocus)
                    root.trackSelected(modelData.path)
            }
            Keys.onReturnPressed: {
                if (trackItem.canInteract)
                    root.playTrackRequested(trackItem.canonicalIndex)
            }
            Keys.onEnterPressed: {
                if (trackItem.canInteract)
                    root.playTrackRequested(trackItem.canonicalIndex)
            }
            Keys.onSpacePressed: event => {
                if (root.selectionMode) {
                    root.selectionToggleRequested(
                        modelData.path,
                        (event.modifiers & Qt.ShiftModifier) !== 0)
                    event.accepted = true
                }
            }
            Keys.onPressed: event => {
                if (event.key === Qt.Key_Menu
                        || (event.key === Qt.Key_F10
                            && (event.modifiers & Qt.ShiftModifier))) {
                    MichiAccessibility.noteKeyboard()
                    trackItem.selectExactTarget()
                    trackMenu.popup()
                    event.accepted = true
                }
            }
            Keys.onUpPressed: event => {
                if (event.modifiers & Qt.AltModifier && root.reorderEnabled
                        && !root.selectionMode) {
                    if (trackItem.canonicalIndex > 0) {
                        root.moveTrackRequested(
                            trackItem.canonicalIndex, trackItem.canonicalIndex - 1)
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else {
                    event.accepted = false
                }
            }
            Keys.onDownPressed: event => {
                if (event.modifiers & Qt.AltModifier && root.reorderEnabled
                        && !root.selectionMode) {
                    if (trackItem.canonicalIndex < root.rows.length - 1) {
                        root.moveTrackRequested(
                            trackItem.canonicalIndex, trackItem.canonicalIndex + 1)
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else {
                    event.accepted = false
                }
            }

            background: Rectangle {
                radius: 5
                color: trackItem.pressed ? MichiSemanticColors.surfacePressed
                    : trackItem.isSelected
                        ? MichiSemanticColors.rowSelected
                        : trackItem.hovered || trackItem.visualFocus
                            ? MichiSemanticColors.rowHover : "transparent"
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing {
                    visualFocus: trackItem.visualFocus
                        && MichiAccessibility.keyboardMode
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: MichiSpacing.md
                anchors.rightMargin: MichiSpacing.md
                height: 1
                color: MichiSemanticColors.rowDivider
                visible: !trackItem.isSelected
            }

            PlaylistTrackContextMenu {
                id: trackMenu
                titleText: modelData.title || modelData.displayName || ""
                artistText: modelData.artist || ""
                albumText: modelData.album || ""
                artworkPath: modelData.artworkPath || ""
                formatKey: modelData.codec
                    ? String(modelData.codec).toLowerCase() : "unknown"
                formatLabel: modelData.qualityLabel || (modelData.codec
                    ? String(modelData.codec).toUpperCase() : "UNKNOWN")
                favorite: trackItem.isFavorite
                canPlayNow: trackItem.canInteract
                canQueue: trackItem.canInteract && (
                    trackItem.hasStableTrackId
                        ? (typeof library !== "undefined" && library
                            && library.canQueueTracks)
                        : (typeof queue !== "undefined" && queue))
                // Shared Library→Playlist picker/create/properties consumers
                // are not wired productively yet. Fail closed: no dead items.
                canAddToPlaylist: false
                canAddToNewPlaylist: false
                canFavorite: typeof library !== "undefined" && library
                canGoToAlbum: false
                canGoToArtist: false
                canShowProperties: false
                canMoveUp: trackItem.canonicalIndex > 0
                    && root.reorderEnabled && !root.selectionMode
                canMoveDown: trackItem.canonicalIndex < root.rows.length - 1
                    && root.reorderEnabled && !root.selectionMode

                onPlayNowRequested: if (trackItem.canInteract)
                    root.playTrackRequested(trackItem.canonicalIndex)
                onQueueRequested: {
                    if (!trackItem.canInteract)
                        return
                    if (trackItem.hasStableTrackId
                            && typeof library !== "undefined" && library
                            && library.canQueueTracks) {
                        // PR #232 contract: preserve stable identity in Queue.
                        library.queue_track_by_id(String(modelData.trackId))
                    } else if (!trackItem.hasStableTrackId
                            && typeof queue !== "undefined" && queue) {
                        // Explicit legacy fallback only; never preferred.
                        queue.add_file(modelData.path)
                    }
                }
                onFavoriteRequested: trackItem.toggleFavorite()
                onRemoveRequested:
                    root.removeTrackRequested(trackItem.canonicalIndex)
                onMoveUpRequested: if (trackItem.canonicalIndex > 0)
                    root.moveTrackRequested(
                        trackItem.canonicalIndex, trackItem.canonicalIndex - 1)
                onMoveDownRequested: if (trackItem.canonicalIndex < root.rows.length - 1)
                    root.moveTrackRequested(
                        trackItem.canonicalIndex, trackItem.canonicalIndex + 1)
            }
        }
    }
}
