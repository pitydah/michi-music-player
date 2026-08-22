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
    implicitHeight: 240
    scale: hover.hovered ? 1.015 : 1
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: artist ? artist.name : "Artist"
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); activated() }

    MichiGlassSurface {
        anchors.fill: parent
        elevation: "subtle"
        contentPadding: MichiSpacing.sm
        shadowed: hover.hovered || root.selected
        textured: false
        accented: root.selected
        accentColor: MichiPalette.auroraCyan

        Rectangle {
            anchors.fill: parent
            color: tap.pressed ? MichiSemanticColors.surfacePressed
                : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
            radius: root.selected ? MichiRadius.lg : MichiRadius.md
            Behavior on color {
                enabled: !MichiAccessibility.reducedMotion
                ColorAnimation { duration: MichiMotion.micro }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: MichiSpacing.sm

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: width

                Artwork {
                    anchors.fill: parent
                    radius: MichiRadius.md
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
                    sourcePath: root.artist ? root.artist.artworkPath : ""
                    fallbackText: root.artist ? root.artist.name : "A"
                }

                Rectangle {
                    anchors.fill: parent
                    radius: MichiRadius.md
                    color: hover.hovered
                        ? MichiSemanticColors.artworkScrimHover : "transparent"
                    opacity: hover.hovered ? 1 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs

                MichiText {
                    Layout.fillWidth: true
                    text: root.artist ? root.artist.name : ""
                    role: "body"
                    font.weight: Font.DemiBold
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
                    color: root.selected ? MichiPalette.auroraCyan : MichiPalette.textMuted
                    elide: Text.ElideRight
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    MichiFocusRing {
        anchors.fill: parent
        visualFocus: root.activeFocus && MichiAccessibility.keyboardMode
    }

    Behavior on scale {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        id: tap
        onTapped: {
            MichiAccessibility.notePointer()
            root.forceActiveFocus()
            root.activated()
        }
    }
}
