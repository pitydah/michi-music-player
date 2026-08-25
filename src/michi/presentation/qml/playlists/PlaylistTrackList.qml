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
    property int selectedIndex: -1
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
    property bool narrow: false            // <700px: title/artist grouped

    signal playTrackRequested(int index)
    signal trackSelected(int index)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

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
            if (currentIndex >= 0 && currentIndex < root.rows.length)
                root.playTrackRequested(currentIndex)
        }
        Keys.onEnterPressed: {
            if (currentIndex >= 0 && currentIndex < root.rows.length)
                root.playTrackRequested(currentIndex)
        }

        // Reorder by drag & drop: drop line + move to the target row
        DropArea {
            anchors.fill: parent
            keys: ["application/x-michi-playlist-index"]

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

        // Insertion indicator for the drag reorder
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

            readonly property bool isPlaying: typeof playback !== "undefined"
                && playback && modelData.path
                && playback.currentPath === modelData.path
            readonly property bool isSelected: root.selectedIndex === index

            // Distinct states: selected = quiet elevation; playing = accent
            // title + animated indicator; both combine cleanly.
            contentItem: RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiSpacing.md
                anchors.rightMargin: MichiSpacing.sm
                spacing: MichiSpacing.md

                // Track number / playing indicator (36-40px) — doubles as
                // the drag handle for reordering (M7)
                Item {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 40

                    Drag.active: dragHandler.active
                    Drag.source: trackItem
                    Drag.supportedActions: Qt.MoveAction
                    Drag.mimeData: { "application/x-michi-playlist-index": index }
                    Drag.hotSpot.x: width / 2
                    Drag.hotSpot.y: height / 2

                    DragHandler {
                        id: dragHandler
                        acceptedButtons: Qt.LeftButton
                        cursorShape: Qt.OpenHandCursor
                        onActiveChanged: {
                            if (active)
                                trackItem.opacity = 0.45
                            else
                                trackItem.opacity = 1
                        }
                    }

                    MichiText {
                        anchors.centerIn: parent
                        visible: !trackItem.isPlaying
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

                // Track artwork 36px, radius 4, 8-12px gap to title
                Artwork {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    sourcePath: modelData.artworkPath || ""
                    fallbackText: modelData.title || modelData.displayName || "T"
                    radius: 4
                }

                // Title (heavier) + grouped artist on narrow widths
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
                    Layout.preferredWidth: 72
                    text: (modelData.qualityLabel && modelData.qualityLabel !== "")
                        ? modelData.qualityLabel : ""
                    role: "technical"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                }

                MichiText {
                    Layout.preferredWidth: 54
                    text: modelData.durationMs > 0 ? MichiFormat.formatDuration(modelData.durationMs) : ""
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    horizontalAlignment: Text.AlignRight
                }

                // Context actions — quiet until the row is hovered/focused
                MichiIconButton {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "heart"
                    accessibleName: typeof library !== "undefined" && library
                        && library.favoritePaths.indexOf(modelData.path) !== -1
                        ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    selected: typeof library !== "undefined" && library
                        && library.favoritePaths.indexOf(modelData.path) !== -1
                    opacity: trackItem.hovered || trackItem.visualFocus ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                    onClicked: {
                        if (typeof library !== "undefined" && library)
                            library.toggle_favorite(modelData.path)
                    }
                }
                MichiIconButton {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "more"
                    accessibleName: qsTr("More options for ") + modelData.title
                    opacity: trackItem.hovered || trackItem.visualFocus ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                    onClicked: trackMenu.popup()
                }
            }

            // Selection on click; playback on double-click / Enter
            onClicked: {
                root.trackSelected(index)
                root.playTrackRequested(index)
            }
            // Keyboard navigation feedback: arrow keys move the ListView
            // currentIndex, so the focused row must also become the visible
            // selected row (otherwise the cursor moves invisibly)
            onActiveFocusChanged: {
                if (activeFocus)
                    root.trackSelected(index)
            }
            Keys.onReturnPressed: root.playTrackRequested(index)
            Keys.onEnterPressed: root.playTrackRequested(index)
            Keys.onUpPressed: event => {
                if (event.modifiers & Qt.AltModifier) {
                    if (index > 0) {
                        root.moveTrackRequested(index, index - 1)
                        // keep the keyboard cursor on the moved row (the
                        // delegate reorders underneath the focus)
                        root.trackSelected(index - 1)
                        trackList.currentIndex = index - 1
                        if (trackList.currentItem)
                            trackList.currentItem.forceActiveFocus()
                        event.accepted = true
                    }
                }
            }
            Keys.onDownPressed: event => {
                if (event.modifiers & Qt.AltModifier) {
                    if (index < root.rows.length - 1) {
                        root.moveTrackRequested(index, index + 1)
                        root.trackSelected(index + 1)
                        trackList.currentIndex = index + 1
                        if (trackList.currentItem)
                            trackList.currentItem.forceActiveFocus()
                        event.accepted = true
                    }
                }
            }

            // Quiet states: normal transparent, hover +0.035, selected +0.06,
            // pressed adds the standard press surface
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
                MichiFocusRing { visualFocus: trackItem.visualFocus && MichiAccessibility.keyboardMode }
            }

            // Hairline separator, near-invisible
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

            MichiMenu {
                id: trackMenu
                MenuItem {
                    text: qsTr("Play")
                    onTriggered: root.playTrackRequested(index)
                }
                MenuItem {
                    text: qsTr("Add to Queue")
                    onTriggered: queue.add_file(modelData.path)
                }
                MichiSeparator { }
                MenuItem {
                    text: qsTr("Remove from playlist")
                    onTriggered: root.removeTrackRequested(index)
                }
                MenuItem {
                    text: qsTr("Move Up")
                    enabled: index > 0
                    onTriggered: root.moveTrackRequested(index, index - 1)
                }
                MenuItem {
                    text: qsTr("Move Down")
                    enabled: index < root.rows.length - 1
                    onTriggered: root.moveTrackRequested(index, index + 1)
                }
            }
        }
    }
}
