import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property string title: ""
    property string artist: ""
    property string album: ""
    property string duration: ""
    property int durationMs: 0
    property string quality: ""
    property string trackId: ""
    property string filePath: ""
    property string albumKey: ""
    property string artistKey: ""
    property string formatKey: "unknown"
    property string formatLabel: "UNKNOWN"
    property string codec: ""
    property string container: ""
    property string dsdRate: ""
    property int sampleRateHz: 0
    property int bitDepth: 0
    property int bitrateBps: 0
    property int channels: 0
    property int fileSize: 0
    property string genre: ""
    property string composer: ""
    property int year: 0
    property string numberText: ""
    property bool playing: false
    property bool selected: false
    property bool interactive: true
    property bool unavailable: false
    property bool favorite: false
    property bool showFavorite: false
    property bool showAddToPlaylist: false
    property bool showInspector: false
    property bool showRemove: false
    property bool canQueue: false
    property bool canGoToAlbum: albumKey.length > 0
    property bool canGoToArtist: artistKey.length > 0
    property bool canMoveUp: false
    property bool canMoveDown: false
    property bool sharedGeometry: false
    property bool showTechnicalColumns: false
    property bool showActions: true
    property bool useDefaultContextMenu: true
    property real titleColumnWidth: LibraryTrackColumnState.titleWidth
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showQualityColumn: MichiThemeState.precisionMode
    property bool showDurationColumn: true
    property string artworkPath: ""
    property bool showArtwork: true
    // Video/perceptual recovery: action affordances remain quiet but visible.
    // 0.18 made the heart/more controls read as disabled or absent.
    readonly property real idleActionOpacity: 0.34
    signal activated()
    signal favoriteToggled()
    signal addToPlaylistRequested()
    signal inspectorRequested()
    signal removeRequested()
    signal queueRequested()
    signal goToAlbumRequested()
    signal goToArtistRequested()
    signal selectedRequested()
    signal moveUpRequested()
    signal moveDownRequested()
    signal contextMenuRequested()
    readonly property string durationText: duration.length > 0
        ? duration : MichiFormat.formatDuration(durationMs)
    implicitHeight: showArtwork
        ? Math.max(MichiThemeState.rowHeight, 44)
        : Math.max(MichiThemeState.rowHeight, MichiMetrics.controlMedium)
    color: selected || playing ? MichiSemanticColors.surfaceSelected
        : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    radius: MichiRadius.sm
    border.width: selected || playing ? 1 : 0
    border.color: playing ? MichiSemanticColors.auroraCyanBorder
        : MichiSemanticColors.auroraBorderSubtle
    opacity: unavailable ? 0.55 : 1
    activeFocusOnTab: root.interactive
    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist.length > 0 ? " by " + artist : "")
    Keys.onEnterPressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            MichiAccessibility.noteKeyboard()
            root.openContextMenu()
            event.accepted = true
        } else if (event.key === Qt.Key_PageDown) {
            MichiAccessibility.noteKeyboard()
            root.moveByPage(1)
            event.accepted = true
        } else if (event.key === Qt.Key_PageUp) {
            MichiAccessibility.noteKeyboard()
            root.moveByPage(-1)
            event.accepted = true
        }
    }

    function moveByPage(direction) {
        var view = root.ListView.view
        if (!view || view.count <= 0)
            return
        var pageSize = Math.max(1, Math.floor(view.height / root.height) - 1)
        view.currentIndex = Math.max(0, Math.min(view.count - 1,
            view.currentIndex + direction * pageSize))
        view.positionViewAtIndex(view.currentIndex, ListView.Contain)
    }

    function openContextMenu() {
        root.selectedRequested()
        if (root.useDefaultContextMenu)
            contextMenu.popup()
        else
            root.contextMenuRequested()
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md
        Item {
            Layout.preferredWidth: root.sharedGeometry
                ? LibraryTrackColumnState.numberWidth : 20
            Layout.fillHeight: true
            MichiPlayingIndicator {
                anchors.centerIn: parent
                playing: root.playing
                visible: root.playing
                width: 16
            }
            MichiText {
                anchors.centerIn: parent
                visible: !root.playing && root.numberText.length > 0
                text: root.numberText
                role: "technical"
                technical: true
            }
        }
        Artwork {
            visible: root.showArtwork && (!root.sharedGeometry
                || LibraryTrackColumnState.artworkVisible)
            Layout.preferredWidth: root.sharedGeometry
                ? LibraryTrackColumnState.artworkWidth
                : (MichiThemeState.density === "comfortable" ? 36 : 30)
            Layout.preferredHeight: Layout.preferredWidth
            Layout.alignment: Qt.AlignVCenter
            sourcePath: root.artworkPath
            fallbackText: root.album || root.title || "T"
            radius: MichiRadius.xs
            requestedSize: Math.round(Layout.preferredWidth * Screen.devicePixelRatio)
        }
        MichiText {
            visible: !root.sharedGeometry || LibraryTrackColumnState.titleVisible
            Layout.fillWidth: !root.sharedGeometry
            Layout.preferredWidth: root.sharedGeometry ? root.titleColumnWidth : -1
            text: root.title
            role: "body"
            font.weight: root.playing || root.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showArtistColumn && (!root.sharedGeometry
                || LibraryTrackColumnState.artistVisible)
            Layout.preferredWidth: root.sharedGeometry
                ? LibraryTrackColumnState.artistWidth : 160
            text: root.artist
            role: "secondary"
            elide: Text.ElideRight
        }
        MichiText {
            Layout.preferredWidth: root.sharedGeometry
                ? LibraryTrackColumnState.albumWidth : 180
            text: root.album
            role: "secondary"
            visible: root.showAlbumColumn && (!root.sharedGeometry
                || LibraryTrackColumnState.albumVisible)
            elide: Text.ElideRight
        }
        MichiText { Layout.preferredWidth: 150; text: root.quality; role: "technical"; technical: true; visible: !root.sharedGeometry && root.showQualityColumn; elide: Text.ElideRight }
        Item {
            visible: root.showTechnicalColumns && LibraryTrackColumnState.formatVisible
            Layout.preferredWidth: LibraryTrackColumnState.formatWidth
            Layout.fillHeight: true
            MichiFormatBadge {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                formatKey: root.formatKey
                displayLabel: root.formatLabel
            }
        }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.sampleRateVisible; Layout.preferredWidth: LibraryTrackColumnState.sampleRateWidth; text: root.sampleRateHz > 0 ? (root.sampleRateHz / 1000) + " kHz" : ""; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.bitDepthVisible; Layout.preferredWidth: LibraryTrackColumnState.bitDepthWidth; text: root.bitDepth > 0 ? root.bitDepth + "-bit" : ""; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.dsdRateVisible; Layout.preferredWidth: LibraryTrackColumnState.dsdRateWidth; text: root.dsdRate; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.bitrateVisible; Layout.preferredWidth: LibraryTrackColumnState.bitrateWidth; text: root.bitrateBps > 0 ? Math.round(root.bitrateBps / 1000) + " kbps" : ""; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.channelsVisible; Layout.preferredWidth: LibraryTrackColumnState.channelsWidth; text: root.channels > 0 ? root.channels + " ch" : ""; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.fileSizeVisible; Layout.preferredWidth: LibraryTrackColumnState.fileSizeWidth; text: root.fileSize > 0 ? MichiFormat.formatFileSize(root.fileSize) : ""; role: "technical"; technical: true; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.genreVisible; Layout.preferredWidth: LibraryTrackColumnState.genreWidth; text: root.genre; role: "secondary"; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.composerVisible; Layout.preferredWidth: LibraryTrackColumnState.composerWidth; text: root.composer; role: "secondary"; elide: Text.ElideRight }
        MichiText { visible: root.showTechnicalColumns && LibraryTrackColumnState.yearVisible; Layout.preferredWidth: LibraryTrackColumnState.yearWidth; text: root.year > 0 ? root.year : ""; role: "technical"; technical: true; horizontalAlignment: Text.AlignRight }
        MichiText { Layout.preferredWidth: root.sharedGeometry ? LibraryTrackColumnState.durationWidth : 48; text: root.durationText; role: "technical"; technical: true; visible: root.showDurationColumn && (!root.sharedGeometry || LibraryTrackColumnState.durationVisible); horizontalAlignment: Text.AlignRight }

        Item {
            visible: root.sharedGeometry && root.showActions
                && LibraryTrackColumnState.actionsVisible
            Layout.preferredWidth: LibraryTrackColumnState.actionsWidth
            Layout.fillHeight: true
            RowLayout {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiSpacing.xxs
                MichiIconButton {
                    visible: root.showFavorite
                    opacity: hover.hovered || root.activeFocus || activeFocus
                        || root.selected || root.favorite ? 1 : root.idleActionOpacity
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "heart"
                    selected: root.favorite
                    accessibleName: root.favorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
                    onClicked: root.favoriteToggled()
                }
                MichiIconButton {
                    visible: root.showRemove
                    opacity: hover.hovered || root.activeFocus || activeFocus
                        || root.selected ? 1 : root.idleActionOpacity
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "trash"
                    accessibleName: qsTr("Remove")
                    onClicked: root.removeRequested()
                }
                MichiIconButton {
                    visible: root.showFavorite || root.showAddToPlaylist
                         || root.showInspector || root.canQueue || root.showRemove
                        || root.canGoToAlbum || root.canGoToArtist
                        || root.canMoveUp || root.canMoveDown
                    opacity: hover.hovered || root.activeFocus || activeFocus
                        || root.selected ? 1 : root.idleActionOpacity
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    iconName: "more"
                    accessibleName: qsTr("More options for %1").arg(root.title)
                    onClicked: root.openContextMenu()
                }
            }
        }
        MichiIconButton {
            visible: !root.sharedGeometry && root.showFavorite
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected || root.favorite ? 1 : root.idleActionOpacity
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "heart"
            selected: root.favorite
            accessibleName: root.favorite ? qsTr("Remove from favorites") : qsTr("Add to favorites")
            onClicked: root.favoriteToggled()
        }
        MichiIconButton {
            visible: !root.sharedGeometry && root.showAddToPlaylist
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : root.idleActionOpacity
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "add"
            accessibleName: qsTr("Add to playlist")
            onClicked: root.addToPlaylistRequested()
        }
        MichiIconButton {
            visible: !root.sharedGeometry && root.showInspector
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : root.idleActionOpacity
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "info"
            accessibleName: qsTr("Track information")
            onClicked: root.inspectorRequested()
        }
        MichiIconButton {
            visible: !root.sharedGeometry && root.showRemove
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : root.idleActionOpacity
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "trash"
            accessibleName: qsTr("Remove")
            onClicked: root.removeRequested()
        }
    }
    Rectangle {
        visible: root.playing
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: 2
        height: Math.max(16, parent.height - MichiSpacing.md)
        radius: 1
        color: MichiPalette.auroraCyan
    }
    Rectangle {
        visible: !root.playing && !root.selected
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: MichiSpacing.xl
        anchors.rightMargin: MichiSpacing.sm
        height: 1
        color: MichiSemanticColors.borderSubtle
        opacity: hover.hovered ? 0 : 0.72
    }
    Behavior on color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
    Behavior on border.color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
    HoverHandler { id: hover; cursorShape: root.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor }
    TapHandler { enabled: root.interactive && !root.unavailable; onTapped: { MichiAccessibility.notePointer(); root.forceActiveFocus(); root.activated() } }
    TapHandler {
        acceptedButtons: Qt.RightButton
        enabled: root.interactive
        onTapped: {
            MichiAccessibility.notePointer()
            root.forceActiveFocus()
            root.openContextMenu()
        }
    }
    TrackContextMenu {
        id: contextMenu
        titleText: root.title
        artistText: root.artist
        albumText: root.album
        artworkPath: root.artworkPath
        formatKey: root.formatKey
        formatLabel: root.formatLabel
        canPlayNow: root.interactive && !root.unavailable
        canQueue: root.canQueue
        favorite: root.favorite
        canFavorite: root.showFavorite
        canAddToPlaylist: root.showAddToPlaylist
        canGoToAlbum: root.canGoToAlbum
        canGoToArtist: root.canGoToArtist
        canShowProperties: root.showInspector
        canRemove: root.showRemove
        canMoveUp: root.canMoveUp
        canMoveDown: root.canMoveDown
        onPlayNowRequested: root.activated()
        onQueueRequested: root.queueRequested()
        onFavoriteRequested: root.favoriteToggled()
        onAddToPlaylistRequested: root.addToPlaylistRequested()
        onAddToNewPlaylistRequested: {
            if (typeof library !== "undefined" && library)
                library.request_new_playlist_for_tracks([root.trackId])
        }
        onGoToAlbumRequested: root.goToAlbumRequested()
        onGoToArtistRequested: root.goToArtistRequested()
        onPropertiesRequested: root.inspectorRequested()
        onRemoveRequested: root.removeRequested()
        onMoveUpRequested: root.moveUpRequested()
        onMoveDownRequested: root.moveDownRequested()
    }
    MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
}
