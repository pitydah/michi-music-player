import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistDetailView — PLAYLISTS + playlist_id editorial page.
// One continuous surface: atmospheric hero (cover + identity + compact
// actions) that scrolls away, a sticky quiet column header, and a dense
// track table below. The playlist is a persistent collection — selecting
// and playing a track never requires queue operations (play_track).
Item {
    id: root

    objectName: "playlistDetailView"
    property bool _detailReady: false
    Component.onCompleted: root._detailReady = true
    property string playlistId: ""
    property string selectedTrackPath: ""
    onPlaylistIdChanged: {
        // R4-02 + PL-FINAL-A02: el PARENT es la única autoridad de
        // selección — TODO el estado efímero se resetea al cambiar de
        // playlist: selección, selection mode, búsqueda local, cursor.
        root.selectedTrackPath = ""
        root.checkedTrackPaths = []
        root.shiftAnchorPath = ""
        root.selectionMode = false
        if (playlists)
            playlists.set_playlist_search_query("")
        if (root._detailReady)
            trackList.resetForPlaylist()
    }
    signal backRequested()
    signal playRequested()
    signal shuffleRequested()
    signal togglePinRequested()
    signal customizeAppearanceRequested(string playlistId)
    signal renameRequested(string playlistId, string playlistName)
    signal deleteRequested(string playlistId, string playlistName)
    signal removeTrackRequested(int index)
    signal removeTracksRequested(var indices)
    signal moveTrackRequested(int fromIndex, int toIndex)
    signal playTrackRequested(int index)
    signal addMusicRequested()
    signal editDescriptionRequested(string playlistId, string description)

    // PL-FINAL-A01/A02: la selección multiselect se identifica por PATH
    // (identidad estable). Los índices son posiciones derivadas del estado
    // canónico y NUNCA se usan como identidad persistente de selección.
    property bool selectionMode: false
    property var checkedTrackPaths: []
    // PL-FINAL-A11: shift-range — anchor del rango (path) + orden visible
    // actual; el rango se calcula sobre las rows visibles AL MOMENTO.
    property string shiftAnchorPath: ""
    readonly property bool searchActive: playlists
        && playlists.playlistSearchQuery.length > 0
    readonly property bool hasChecked: root.checkedTrackPaths.length > 0

    // PL-FINAL-A10: UNION deduplicada de paths (Select All visible
    // acumula; nunca reemplaza la selección existente).
    function _unionPaths(a, b) {
        var result = a.slice()
        for (var i = 0; i < b.length; ++i) {
            if (result.indexOf(b[i]) === -1)
                result.push(b[i])
        }
        return result
    }

    // Hero occupies ~30-40% of the first visible screen
    readonly property real heroHeight: Math.max(240, Math.min(300, root.height * 0.36))
    // Sticky column header — completely hidden over the hero (the in-flow
    // header below the hero shows the labels there); fades in with the
    // backplane once the hero scrolls away
    readonly property real stickyHeaderOpacity: trackList
        ? Math.max(0, Math.min(1, (trackList.contentY - (root.heroHeight - 44)) / 44)) : 0
    readonly property bool showArtist: root.width >= 700
    readonly property bool showAlbum: root.width >= 900
    readonly property bool showFormat: root.width > 1200

    // Hero as a Component (ListView.header requires QQmlComponent — an
    // instantiated Item cannot be assigned). The wrapper scrolls away as a
    // unit: the editorial hero on top, the quiet column header below it
    // (it only "sticks" via the separate overlay once the hero leaves).
    // Bindings are null-safe: the header can be instantiated before the
    // bridge context resolves, and they re-evaluate on playlists_changed.
    Component {
        id: heroComponent
        Item {
            id: heroHeader
            objectName: "playlistHeroHeader"
            readonly property var appearance: playlists
                ? playlists.selectedPlaylistAppearance : ({})
            // ListView does not guarantee the implicit dimensions of an
            // arbitrary Item header. Explicit geometry is mandatory: the
            // previous implicit-only wrapper produced a zero-width/height
            // hero whose children leaked into the page without its cover or
            // background.
            width: root.width
            height: root.heroHeight + MichiMetrics.controlSmall
            implicitWidth: width
            implicitHeight: height

            PlaylistHero {
                id: heroItem
                objectName: "playlistHero"
                width: parent.width
                height: root.heroHeight
                playlistName: playlists ? playlists.selectedPlaylistName : ""
                trackCount: playlists ? playlists.playlistTracks.length : 0
                durationMs: playlists ? playlists.selectedPlaylistDurationMs : 0
                // PL-FINAL-05/16: descripcion real + conteo honesto +
                // playable count (Play/Shuffle habilitados solo con tracks
                // reproducibles).
                description: playlists ? playlists.selectedPlaylistDescription : ""
                unavailableCount: playlists ? playlists.playlistUnavailableCount : 0
                availableTrackCount: playlists ? playlists.playlistAvailableTrackCount : 0

                // R2 P1-11: EFFECTIVE cover — a vanished managed asset
                // renders the automatic mosaic, never a dead box.
                customCoverPath: playlists ? (playlists.effectiveCustomCoverPath || "") : ""
                mosaicArtworkPaths: playlists ? (playlists.selectedPlaylistMosaicArtworkPaths || []) : []
                // R2 P1-11: effective hero mode — a persisted image whose
                // managed asset vanished degrades to auto (never a dead
                // render); persisted intent stays untouched.
                heroMode: playlists ? playlists.effectiveHeroMode : "auto"
                heroSolidColor: parent.appearance.heroSolidColor || MichiPalette.playlistHeroTop
                heroGradientColors: parent.appearance.heroGradientColors || [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
                heroGradientAngle: parent.appearance.heroGradientAngle === undefined
                    ? 135 : parent.appearance.heroGradientAngle
                heroImagePath: parent.appearance.effectiveHeroImagePath || ""
                autoHeroColors: playlists ? playlists.selectedPlaylistAutoHeroColors : [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid, MichiPalette.playlistHeroBottom]
                // PL-FINAL-09: focal del hero image (persistido con Apply).
                heroFocalX: parent.appearance.heroFocalX === undefined
                    ? 0.5 : parent.appearance.heroFocalX
                heroFocalY: parent.appearance.heroFocalY === undefined
                    ? 0.5 : parent.appearance.heroFocalY

                // R2.1-07: signals wired INLINE (the ListView headerItem is
                // this wrapper Item, NOT the hero — a Connections on
                // headerItem never matches the hero's signals)
                onPlayRequested: root.playRequested()
                onShuffleRequested: root.shuffleRequested()
                onMoreRequested: detailMenu.popup()
                onCustomizeAppearanceRequested: root.customizeAppearanceRequested(root.playlistId)

                onAddTracksRequested: root.addMusicRequested()
            }

            PlaylistColumnHeader {
                anchors.top: heroItem.bottom
                width: parent.width
                showArtist: width >= 700
                showAlbum: width >= 900
                showFormat: width > 1200
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Top bar (fixed) — quiet back affordance only
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.leftMargin: MichiSpacing.xl
            Layout.rightMargin: MichiSpacing.xl
            spacing: MichiSpacing.sm
            z: 6

            MichiIconButton {
                iconName: "back"
                accessibleName: qsTr("Back to All Playlists")
                onClicked: root.backRequested()
            }
            // PL-FINAL-14/15: toolbar local — búsqueda dentro de la
            // playlist + selection mode. La búsqueda NUNCA toca el search
            // global de la biblioteca.
            MichiTextField {
                Layout.fillWidth: true
                Layout.maximumWidth: 320
                Layout.preferredHeight: MichiMetrics.controlMedium
                placeholderText: qsTr("Search in playlist")
                text: playlists.playlistSearchQuery
                onTextChanged: playlists.set_playlist_search_query(text)
                Accessible.name: qsTr("Search tracks in this playlist")
            }
            MichiButton {
                visible: !root.selectionMode
                text: qsTr("Select")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlMedium
                accessibleName: qsTr("Select multiple tracks")
                onClicked: {
                    root.checkedTrackPaths = []
                    root.shiftAnchorPath = ""
                    root.selectionMode = true
                }
            }
            // PL-FINAL-15/10-10-FINAL-04: en selection mode — select all
            // visible (UNION), clear, remove batch (por PATH) + done.
            MichiButton {
                visible: root.selectionMode
                text: qsTr("Select all visible")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlMedium
                enabled: (playlists.playlistTrackRows || []).length > 0
                accessibleName: qsTr("Select every visible track")
                onClicked: {
                    // PL-10-FINAL-04: UNION — nunca reemplaza la selección
                    // existente (paths de otros filtros se conservan).
                    var rows = playlists.playlistTrackRows || []
                    var visible = []
                    for (var i = 0; i < rows.length; ++i)
                        visible.push(rows[i].path)
                    root.checkedTrackPaths = root._unionPaths(
                        root.checkedTrackPaths, visible)
                }
            }
            MichiButton {
                visible: root.selectionMode
                text: qsTr("Clear")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlMedium
                enabled: root.hasChecked
                accessibleName: qsTr("Clear selection")
                onClicked: {
                    root.checkedTrackPaths = []
                    root.shiftAnchorPath = ""
                }
            }
            MichiButton {
                visible: root.selectionMode
                text: qsTr("Remove %1").arg(root.checkedTrackPaths.length)
                variant: "danger"
                implicitHeight: MichiMetrics.controlMedium
                enabled: root.hasChecked
                accessibleName: qsTr("Remove selected tracks from playlist")
                onClicked: root.removeTracksRequested(root.checkedTrackPaths.slice())
            }
            MichiButton {
                visible: root.selectionMode
                text: qsTr("Done")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlMedium
                accessibleName: qsTr("Exit selection mode")
                onClicked: {
                    root.checkedTrackPaths = []
                    root.shiftAnchorPath = ""
                    root.selectionMode = false
                }
            }
            Item { Layout.fillWidth: true }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // Sticky column header — fades in (labels + backplane) only
            // while the hero scrolls away; hidden over the hero itself
            Rectangle {
                id: columnHeaderBar
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 34
                z: 5
                color: MichiSemanticColors.backplane
                opacity: root.stickyHeaderOpacity
                clip: true
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                }

                PlaylistColumnHeader {
                    anchors.fill: parent
                    showArtist: root.showArtist
                    showAlbum: root.showAlbum
                    showFormat: root.showFormat
                }
            }

            PlaylistTrackList {
                id: trackList
                anchors.fill: parent
                rows: playlists.playlistTrackRows
                selectedTrackPath: root.selectedTrackPath
                showArtistColumn: root.width >= 700
                showAlbumColumn: root.width >= 900
                showFormatColumn: root.width > 1200
                narrow: root.width < 700
                heroComponent: heroComponent
                // PL-FINAL-14/15: selection mode + reorder gated por search.
                selectionMode: root.selectionMode
                checkedPaths: root.checkedTrackPaths
                reorderEnabled: !root.searchActive && !root.selectionMode

                onTrackSelected: path => root.selectedTrackPath = path
                // R4-11: el Detail re-emite el INTENT — ContentHost traduce.
                onPlayTrackRequested: index => root.playTrackRequested(index)
                onRemoveTrackRequested: index => root.removeTrackRequested(index)
                onMoveTrackRequested: (f, t) => root.moveTrackRequested(f, t)
                onSelectionToggleRequested: (path, shiftHeld) => {
                    // PL-FINAL-A01/A11: toggle por PATH (identidad). Con
                    // Shift: rango desde el anchor sobre las rows VISIBLES
                    // actuales (proyección filtrada) — nunca índices.
                    if (shiftHeld && root.shiftAnchorPath.length > 0) {
                        var rows = playlists.playlistTrackRows || []
                        var anchorPos = -1
                        var targetPos = -1
                        for (var i = 0; i < rows.length; ++i) {
                            if (rows[i].path === root.shiftAnchorPath)
                                anchorPos = i
                            if (rows[i].path === path)
                                targetPos = i
                        }
                        if (anchorPos >= 0 && targetPos >= 0) {
                            var lo = Math.min(anchorPos, targetPos)
                            var hi = Math.max(anchorPos, targetPos)
                            var range = []
                            for (var j = lo; j <= hi; ++j)
                                range.push(rows[j].path)
                            root.checkedTrackPaths = root._unionPaths(
                                root.checkedTrackPaths, range)
                            root.shiftAnchorPath = path
                            return
                        }
                    }
                    var i2 = root.checkedTrackPaths.indexOf(path)
                    if (i2 === -1) {
                        root.checkedTrackPaths =
                            root.checkedTrackPaths.concat([path])
                        root.shiftAnchorPath = path
                    } else {
                        var copy = root.checkedTrackPaths.slice()
                        copy.splice(i2, 1)
                        root.checkedTrackPaths = copy
                        if (root.shiftAnchorPath === path)
                            root.shiftAnchorPath = ""
                    }
                }
            }
            // Empty state — hero stays, tracks area shows a quiet prompt.
            // PL-FINAL-14: distingue "sin tracks" de "sin coincidencias".
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: root.heroHeight
                anchors.bottomMargin: MichiSpacing.xl
                visible: playlists.playlistTrackRows.length === 0
                spacing: MichiSpacing.sm

                Item { Layout.fillHeight: true }
                MichiIcon {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 34
                    Layout.preferredHeight: 34
                    name: "playlist"
                    iconColor: MichiPalette.textMuted
                }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.searchActive
                        ? qsTr("No matching tracks")
                        : qsTr("This playlist is empty")
                    role: "section"
                    color: MichiPalette.textPrimary
                }
                MichiText {
                    Layout.alignment: Qt.AlignHCenter
                    visible: !root.searchActive
                    text: qsTr("Add music from your library to start listening.")
                    role: "secondary"
                    color: MichiPalette.textSecondary
                    opacity: 0.65
                }
                Item { Layout.preferredHeight: MichiSpacing.xs }
                MichiButton {
                    Layout.alignment: Qt.AlignHCenter
                    visible: !root.searchActive
                    text: qsTr("Add Music")
                    iconName: "plus"
                    variant: "secondary"
                    implicitHeight: MichiMetrics.controlMedium
                    onClicked: root.addMusicRequested()
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    MichiMenu {
        id: detailMenu
        MenuItem {
            text: qsTr("Shuffle Play")
            // PL-10-FINAL-06: con 0 tracks reproducibles el shuffle está
            // deshabilitado (el handler defensivo de ContentHost tampoco
            // ejecuta nada).
            enabled: playlists && playlists.playlistAvailableTrackCount > 0
            onTriggered: root.shuffleRequested()
        }
        MenuItem {
            text: qsTr("Add tracks…")
            onTriggered: root.addMusicRequested()
        }
        MenuItem {
            objectName: "playlistDetailEditDescriptionAction"
            text: qsTr("Edit description…")
            onTriggered: root.editDescriptionRequested(
                root.playlistId, playlists.selectedPlaylistDescription)
        }
        MenuItem {
            text: qsTr("Customize appearance…")
            onTriggered: root.customizeAppearanceRequested(root.playlistId)
        }
        MenuItem {
            text: playlists.selectedPlaylistPinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.togglePinRequested()
        }
        MenuItem {
            objectName: "playlistDetailRenameAction"
            text: qsTr("Rename…")
            onTriggered: root.renameRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
        MenuItem {
            objectName: "playlistDetailDeleteAction"
            text: qsTr("Delete…")
            onTriggered: root.deleteRequested(
                root.playlistId, playlists.selectedPlaylistName)
        }
    }
}
