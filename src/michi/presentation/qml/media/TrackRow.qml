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
    property string quality: ""
    property bool playing: false
    property bool unavailable: false
    signal activated()
    implicitHeight: MichiThemeState.rowHeight
    color: tap.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    radius: MichiRadius.sm
    opacity: unavailable ? 0.55 : 1
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: title + (artist.length > 0 ? " by " + artist : "")
    Keys.onEnterPressed: if (!unavailable) activated()
    Keys.onReturnPressed: if (!unavailable) activated()

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md
        MichiPlayingIndicator { playing: root.playing; visible: root.playing; Layout.preferredWidth: 16 }
        MichiText { Layout.fillWidth: true; text: root.title; role: "body"; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 160; text: root.artist; role: "secondary"; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 180; text: root.album; role: "secondary"; visible: !MichiThemeState.precisionMode; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 150; text: root.quality; role: "technical"; technical: true; visible: MichiThemeState.precisionMode; elide: Text.ElideRight }
        MichiText { Layout.preferredWidth: 48; text: root.duration; role: "technical"; technical: true; horizontalAlignment: Text.AlignRight }
    }
    HoverHandler { id: tap; cursorShape: root.unavailable ? Qt.ArrowCursor : Qt.PointingHandCursor }
    TapHandler { enabled: !root.unavailable; onTapped: { root.forceActiveFocus(); root.activated() } }
    MichiFocusRing { visualFocus: root.activeFocus }
}
