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
    property bool showArtistColumn: true
    property bool showAlbumColumn: true
    property bool showQualityColumn: false
    property bool showDurationColumn: true
    property string artworkPath: ""
    property bool showArtwork: true
    signal activated()
    signal favoriteToggled()
    signal addToPlaylistRequested()
    signal inspectorRequested()
    signal removeRequested()
    readonly property string durationText: duration.length > 0
        ? duration : MichiFormat.formatDuration(durationMs)
    // Minimum height keeps action icon-buttons (controlMedium = 36px)
    // comfortably contained in every density, artwork rows add their own size.
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
    activeFocusOnTab: root.interactive && !root.unavailable
    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist.length > 0 ? " by " + artist : "")
    Keys.onEnterPressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: if (root.interactive && !root.unavailable) { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_PageDown) {
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

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md
        Item {
            Layout.preferredWidth: 20
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
            visible: root.showArtwork
            Layout.preferredWidth: MichiThemeState.density === "comfortable" ? 36 : 30
            Layout.preferredHeight: Layout.preferredWidth
            Layout.alignment: Qt.AlignVCenter
            sourcePath: root.artworkPath
            fallbackText: root.album || root.title || "T"
            radius: MichiRadius.xs
            requestedSize: Math.round((MichiThemeState.density === "comfortable" ? 36 : 30) * Screen.devicePixelRatio)
        }
        MichiText {
            Layout.fillWidth: true
            text: root.title
            role: "body"
            font.weight: root.playing || root.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showArtistColumn
            Layout.preferredWidth: 160
            text: root.artist
            role: "secondary"
            elide: Text.ElideRight
        }
        MichiText {
            Layout.preferredWidth: 180
            text: root.album
            role: "secondary"
            visible: root.showAlbumColumn
            elide: Text.ElideRight
        }
        MichiText { Layout.preferredWidth: 150; text: root.quality; role: "technical"; technical: true; visible: root.showQualityColumn; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 48; text: root.durationText; role: "technical"; technical: true; visible: root.showDurationColumn; horizontalAlignment: Text.AlignRight }

        MichiIconButton {
            visible: root.showFavorite
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected || root.favorite ? 1 : 0.18
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "heart"
            selected: root.favorite
            accessibleName: root.favorite ? "Remove from favorites" : "Add to favorites"
            onClicked: root.favoriteToggled()
        }
        MichiIconButton {
            visible: root.showAddToPlaylist
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : 0.18
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "add"
            accessibleName: qsTr("Add to playlist")
            onClicked: root.addToPlaylistRequested()
        }
        MichiIconButton {
            visible: root.showInspector
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : 0.18
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "info"
            accessibleName: qsTr("Track information")
            onClicked: root.inspectorRequested()
        }
        MichiIconButton {
            visible: root.showRemove
            opacity: hover.hovered || root.activeFocus || activeFocus
                || root.selected ? 1 : 0.18
            Layout.preferredWidth: MichiMetrics.controlMedium
            Layout.preferredHeight: MichiMetrics.controlMedium
            iconName: "trash"
            accessibleName: qsTr("Remove from queue")
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
    HoverHandler { id: hover; cursorShape: root.interactive && !root.unavailable ? Qt.PointingHandCursor : Qt.ArrowCursor }
    TapHandler { enabled: root.interactive && !root.unavailable; onTapped: { MichiAccessibility.notePointer(); root.forceActiveFocus(); root.activated() } }
    TapHandler {
        acceptedButtons: Qt.RightButton
        enabled: root.interactive && !root.unavailable
        onTapped: { MichiAccessibility.notePointer(); contextMenu.popup() }
    }
    MichiContextMenu {
        id: contextMenu
        canPlay: root.interactive && !root.unavailable
        canFavorite: root.showFavorite
        favorite: root.favorite
        canAddToPlaylist: root.showAddToPlaylist
        canInspect: root.showInspector
        canRemove: root.showRemove
        onPlayRequested: root.activated()
        onFavoriteRequested: root.favoriteToggled()
        onAddToPlaylistRequested: root.addToPlaylistRequested()
        onInspectRequested: root.inspectorRequested()
        onRemoveRequested: root.removeRequested()
    }
    MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
}
