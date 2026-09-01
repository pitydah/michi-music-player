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
    // PL-FINAL-A01: selección por PATH (identidad estable). El Detail es
    // el dueño del Set; esta lista solo proyecta checkboxes.
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
    property bool narrow: false            // <700px: title/artist grouped
    readonly property real contentY: trackList.contentY

    signal playTrackRequested(int index)
    signal trackSelected(string path)
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)
    signal selectionToggleRequested(string path, bool shiftHeld)

    // R3-07/08: rows-driven selection sync — cuando rows cambia (move
    // exitoso), el path seleccionado sigue a su nueva posición.
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
        // R4-02: el child NO escribe selection (autoridad del parent) —
        // solo cursor/presentación. selectedTrackPath es identidad.
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
            // PL-FINAL-14/A04: la tecla global del ListView apunta al
            // índice CANONICO (filter-safe) y respeta canInteract.
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

        // Reorder by drag & drop: drop line + move to the target row.
        // PL-FINAL-14: con filtro de búsqueda activo el reorder se
        // deshabilita por completo (drop nunca reordena posiciones
        // filtradas).
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

            // PL-FINAL-14: TODA acción que llega al Bridge usa el INDEX
            // CANONICO del modelo (la posición real en la playlist). Con
            // un filtro de búsqueda activo, `index` es la posición en la
            // lista FILTRADA y nunca debe usarse como identidad.
            readonly property int canonicalIndex:
                modelData.canonicalIndex !== undefined
                    ? modelData.canonicalIndex : index

            readonly property bool isPlaying: typeof playback !== "undefined"
                && playback && modelData.path
                && playback.currentPath === modelData.path
            readonly property bool isSelected:
                root.selectedTrackPath === modelData.path
            // PL-FINAL-16: un track que la biblioteca no resuelve nunca se
            // borra silenciosamente: queda visible, marcado y sin playback.
            readonly property bool unavailable: modelData.available === false
                || modelData.unavailableReason !== undefined
                && modelData.unavailableReason !== ""
            // PL-FINAL-A04: UNA SOLA autoridad de interacción — canInteract
            // define el permiso para play/queue. Todas las rutas (click,
            // teclado, menú, shortcuts) usan ESTA propiedad.
            readonly property bool canInteract: !trackItem.unavailable

            // R3-09: reveal incluye el focus de los PROPIOS controles —
            // un keyboard user que tabee hasta ellos los ve (opacity 1
            // con activeFocus del child, aunque trackItem no tenga
            // visualFocus). NO se sacan del tab order.
            readonly property bool actionsVisible:
                trackItem.hovered || trackItem.visualFocus
                || favoriteButton.activeFocus || moreButton.activeFocus
                || trackMenu.visible

            // Distinct states: selected = quiet elevation; playing = accent
            // title + animated indicator; both combine cleanly.
            // PL-10-FINAL-03: la row interaction surface (MouseArea) vive
            // DETRÁS del RowLayout de controles — el hit test QML salta el
            // layout (sin handlers) y entrega el click del fondo al
            // MouseArea con los modifiers REALES; los controles interactivos
            // (checkbox/favorite/more) consumen los suyos.
            contentItem: Item {
                anchors.fill: parent

                MouseArea {
                    id: rowSurface
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: Qt.PointingHandCursor
                    onClicked: mouse => {
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

                // Track number / playing indicator (36-40px) — doubles as
                // the drag handle for reordering (M7)
                Item {
                    Layout.preferredWidth: root.selectionMode ? 40 : 36
                    Layout.preferredHeight: 40

                    // PL-FINAL-15: en selection mode el handle de drag
                    // desaparece y entra el checkbox; el drag reorder solo
                    // es válido sin filtro de búsqueda activo.
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
                        onActiveChanged: {
                            if (active)
                                trackItem.opacity = 0.45
                            else
                                trackItem.opacity = 1
                        }
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
                    // PL-FINAL-24: 72px truncaba "FLAC · 24/96" — mínimo
                    // responsivo para no cortar etiquetas reales.
                    Layout.preferredWidth: Math.max(96, trackList.width * 0.13)
                    Layout.minimumWidth: 96
                    Layout.maximumWidth: 200
                    text: (modelData.qualityLabel && modelData.qualityLabel !== "")
                        ? modelData.qualityLabel : ""
                    role: "technical"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                }

                // PL-FINAL-16: estado explícito de track no disponible —
                // nunca borrado silencioso, nunca playback roto.
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
                    accessibleName: typeof library !== "undefined" && library
                        && library.favoritePaths.indexOf(modelData.path) !== -1
                        ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    selected: typeof library !== "undefined" && library
                        && library.favoritePaths.indexOf(modelData.path) !== -1
                    opacity: actionsVisible ? 1 : 0
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
                    onClicked: trackMenu.popup()
                }
                }
            }

            // Keyboard navigation feedback: arrow keys move the ListView
            // currentIndex, so the focused row must also become the visible
            // selected row (otherwise the cursor moves invisibly)
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
                    // PL-10-FINAL-03: Shift+Space = rango sobre las rows
                    // visibles; el Detail calcula el rango por PATH.
                    root.selectionToggleRequested(
                        modelData.path,
                        (event.modifiers & Qt.ShiftModifier) !== 0)
                    event.accepted = true
                }
            }
            Keys.onUpPressed: event => {
                if (event.modifiers & Qt.AltModifier && root.reorderEnabled
                        && !root.selectionMode) {
                    if (trackItem.canonicalIndex > 0) {
                        // R3-08: SOLO el intent. La selección se mantiene
                        // por path; rows cambia → onRowsChanged sincroniza
                        // currentIndex con la posición del path seleccionado.
                        root.moveTrackRequested(
                            trackItem.canonicalIndex, trackItem.canonicalIndex - 1)
                        event.accepted = true
                    } else {
                        event.accepted = false
                    }
                } else {
                    // R3-F1: Up/Down plain → keyNavigation nativo del ListView.
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
                    enabled: trackItem.canInteract
                    onTriggered: root.playTrackRequested(trackItem.canonicalIndex)
                }
                MenuItem {
                    text: qsTr("Add to Queue")
                    // PL-FINAL-A04: canQueue == canInteract — un track
                    // unavailable nunca entra a la queue.
                    enabled: trackItem.canInteract
                    onTriggered: queue.add_file(modelData.path)
                }
                MichiSeparator { }
                MenuItem {
                    text: qsTr("Remove from playlist")
                    onTriggered: root.removeTrackRequested(trackItem.canonicalIndex)
                }
                MenuItem {
                    text: qsTr("Move Up")
                    enabled: trackItem.canonicalIndex > 0 && root.reorderEnabled
                        && !root.selectionMode
                    onTriggered: root.moveTrackRequested(
                        trackItem.canonicalIndex, trackItem.canonicalIndex - 1)
                }
                MenuItem {
                    text: qsTr("Move Down")
                    enabled: trackItem.canonicalIndex < root.rows.length - 1
                        && root.reorderEnabled && !root.selectionMode
                    onTriggered: root.moveTrackRequested(
                        trackItem.canonicalIndex, trackItem.canonicalIndex + 1)
                }
            }
        }
    }
}
