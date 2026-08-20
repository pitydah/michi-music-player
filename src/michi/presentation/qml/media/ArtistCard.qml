import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property var artist: null
    property bool selected: false
    signal activated()

    implicitWidth: 184
    implicitHeight: 88
    scale: hover.hovered ? 1.012 : 1
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: artist ? artist.name : "Artist"
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); activated() }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
        border.width: root.selected || hover.hovered ? 1 : 0
        border.color: root.selected ? MichiPalette.auroraBlue : MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        spacing: MichiSpacing.md

        Rectangle {
            Layout.preferredWidth: 48
            Layout.preferredHeight: 48
            radius: 24
            color: MichiSemanticColors.controlSurfaceStrong
            border.width: 1
            border.color: Qt.rgba(0.129, 0.839, 0.902, 0.2)
            MichiIcon {
                anchors.centerIn: parent
                name: "artist"
                width: 20
                height: 20
                iconColor: MichiPalette.auroraCyan
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            MichiText {
                Layout.fillWidth: true
                text: root.artist ? root.artist.name : ""
                role: "body"
                font.weight: Font.Medium
                elide: Text.ElideRight
            }
            MichiText {
                Layout.fillWidth: true
                text: root.artist
                    ? root.artist.albumCount + " albums · " + root.artist.trackCount + " tracks"
                    : ""
                role: "secondary"
                elide: Text.ElideRight
            }
        }
    }

    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: { MichiAccessibility.notePointer(); root.forceActiveFocus(); root.activated() } }
}
