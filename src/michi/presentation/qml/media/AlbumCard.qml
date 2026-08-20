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
    scale: tap.hovered ? 1.018 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: album ? album.title + " by " + album.artist : "Album"
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); activated() }

    Rectangle {
        x: 2
        y: 4
        width: parent.width - 4
        height: parent.height - 4
        radius: MichiRadius.lg
        color: tap.hovered ? MichiSemanticColors.artworkScrimHover
            : MichiSemanticColors.artworkScrim
        opacity: root.selected || tap.hovered ? 1 : 0
        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation { duration: MichiMotion.micro }
        }
    }
    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: tap.hovered ? MichiSemanticColors.surfaceHover : "transparent"
        border.width: root.selected || tap.hovered ? 1 : 0
        border.color: root.selected ? MichiPalette.auroraBlue : MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
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
    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
    }
    HoverHandler { id: tap; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: { MichiAccessibility.notePointer(); root.forceActiveFocus(); root.activated() } }
}
