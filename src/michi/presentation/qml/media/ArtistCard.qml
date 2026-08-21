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
    implicitHeight: 224
    scale: hover.hovered ? 1.022 : 1
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: artist ? artist.name : "Artist"
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); activated() }

    MichiGlassSurface {
        anchors.fill: parent
        elevation: hover.hovered || root.selected ? "elevated" : "subtle"
        contentPadding: 0
        shadowed: hover.hovered || root.selected
        textured: true
        accented: root.selected
        accentColor: MichiPalette.auroraCyan
        MichiFocusRing { visualFocus: root.activeFocus && MichiAccessibility.keyboardMode }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        spacing: MichiSpacing.sm

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Math.min(root.width - MichiSpacing.xl, 142)
            Layout.preferredHeight: width
            radius: width / 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: MichiPalette.auroraBlue }
                GradientStop { position: 0.52; color: MichiPalette.auroraCyan }
                GradientStop { position: 1; color: MichiPalette.auroraPurple }
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: root.selected || hover.hovered ? 2 : 3
                radius: width / 2
                color: MichiPalette.obsidianDeep

                Artwork {
                    anchors.fill: parent
                    anchors.margins: 3
                    radius: width / 2
                    requestedSize: 256
                    sourcePath: root.artist ? root.artist.artworkPath : ""
                    fallbackText: root.artist ? root.artist.name : "A"
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.rightMargin: 8
                anchors.bottomMargin: 8
                width: 24
                height: 24
                radius: 12
                color: MichiSemanticColors.controlSurfaceStrong
                border.width: 1
                border.color: MichiSemanticColors.auroraCyanBorderStrong
                MichiIcon {
                    anchors.centerIn: parent
                    width: 13
                    height: 13
                    name: "artist"
                    iconColor: MichiPalette.auroraCyan
                }
            }
        }

        MichiText {
            Layout.fillWidth: true
            text: root.artist ? root.artist.name : ""
            role: "body"
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: root.artist
                ? root.artist.albumCount
                    + (root.artist.albumCount === 1 ? " album · " : " albums · ")
                    + root.artist.trackCount
                    + (root.artist.trackCount === 1 ? " track" : " tracks")
                : ""
            role: "caption"
            color: MichiPalette.textMuted
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }
    }

    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: { MichiAccessibility.notePointer(); root.forceActiveFocus(); root.activated() } }
}
