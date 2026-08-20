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
    signal activated()
    signal favoriteToggled()
    signal addToPlaylistRequested()
    signal inspectorRequested()
    signal removeRequested()
    readonly property string durationText: duration.length > 0
        ? duration : formatDuration(durationMs)
    implicitHeight: MichiThemeState.rowHeight
    color: selected || playing ? MichiSemanticColors.surfaceSelected
        : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    radius: MichiRadius.sm
    opacity: unavailable ? 0.55 : 1
    activeFocusOnTab: root.interactive && !root.unavailable
    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist.length > 0 ? " by " + artist : "")
    Keys.onEnterPressed: if (root.interactive && !root.unavailable) activated()
    Keys.onReturnPressed: if (root.interactive && !root.unavailable) activated()
    Keys.onSpacePressed: if (root.interactive && !root.unavailable) activated()

    function formatDuration(ms) {
        if (ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
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
        MichiText { Layout.fillWidth: true; text: root.title; role: "body"; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 160; text: root.artist; role: "secondary"; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 180; text: root.album; role: "secondary"; visible: !MichiThemeState.precisionMode; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 150; text: root.quality; role: "technical"; technical: true; visible: MichiThemeState.precisionMode; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 48; text: root.durationText; role: "technical"; technical: true; horizontalAlignment: Text.AlignRight }

        MichiIconButton {
            visible: root.showFavorite
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            iconName: "heart"
            selected: root.favorite
            accessibleName: root.favorite ? "Remove from favorites" : "Add to favorites"
            onClicked: root.favoriteToggled()
        }
        MichiIconButton {
            visible: root.showAddToPlaylist
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            iconName: "add"
            accessibleName: "Add to playlist"
            onClicked: root.addToPlaylistRequested()
        }
        MichiIconButton {
            visible: root.showInspector
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            iconName: "info"
            accessibleName: "Track information"
            onClicked: root.inspectorRequested()
        }
        MichiIconButton {
            visible: root.showRemove
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            iconName: "trash"
            accessibleName: "Remove from queue"
            onClicked: root.removeRequested()
        }
    }
    HoverHandler { id: hover; cursorShape: root.interactive && !root.unavailable ? Qt.PointingHandCursor : Qt.ArrowCursor }
    TapHandler { enabled: root.interactive && !root.unavailable; onTapped: { root.forceActiveFocus(); root.activated() } }
    MichiFocusRing { visualFocus: root.activeFocus }
}
