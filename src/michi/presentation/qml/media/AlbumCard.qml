import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property var album: null
    property bool selected: false
    signal activated()
    implicitWidth: 164
    implicitHeight: 206
    focus: false
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: album ? album.title + " by " + album.artist : "Album"
    Keys.onEnterPressed: activated()
    Keys.onReturnPressed: activated()
    Keys.onSpacePressed: activated()

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: tap.hovered ? MichiSemanticColors.surfaceHover : "transparent"
        border.width: root.selected ? 1 : 0
        border.color: MichiPalette.auroraBlue
        Behavior on color { ColorAnimation { duration: MichiMotion.micro } }
        MichiFocusRing { visualFocus: root.activeFocus }
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.sm
        spacing: MichiSpacing.sm
        Artwork {
            Layout.fillWidth: true
            Layout.preferredHeight: width
            sourcePath: root.album && root.album.hasArtwork ? root.album.artworkPath : ""
            fallbackText: root.album ? root.album.title : "?"
            requestedSize: Math.round(width * Screen.devicePixelRatio)
        }
        MichiText {
            Layout.fillWidth: true
            text: root.album ? root.album.title : ""
            role: "body"
            font.weight: Font.Medium
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: root.album ? root.album.artist : ""
            role: "secondary"
            elide: Text.ElideRight
        }
    }
    HoverHandler { id: tap; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: { root.forceActiveFocus(); root.activated() } }
}
