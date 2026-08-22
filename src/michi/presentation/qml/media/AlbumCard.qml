import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Item {
    id: root
    property var album: null
    property bool selected: false
    signal activated()
    implicitWidth: 196
    implicitHeight: 286
    focus: false
    activeFocusOnTab: true
    scale: hover.hovered ? 1.015 : 1
    Accessible.role: Accessible.ListItem
    Accessible.name: album ? album.title + " by " + album.artist : "Album"
    Accessible.description: album ? root.albumDescription() : ""
    Keys.onEnterPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onReturnPressed: { MichiAccessibility.noteKeyboard(); activated() }
    Keys.onSpacePressed: { MichiAccessibility.noteKeyboard(); activated() }

    function albumDescription() {
        var details = []
        if (album.year > 0)
            details.push(String(album.year))
        if (album.trackCount > 0)
            details.push(album.trackCount + (album.trackCount === 1 ? " track" : " tracks"))
        if (album.technicalSummary)
            details.push(album.technicalSummary)
        return details.join(" · ")
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: tap.pressed
            ? MichiSemanticColors.surfacePressed
            : hover.hovered
                ? MichiSemanticColors.surfaceHover
                : root.selected
        border.width: 1
        border.color: root.selected
            ? MichiSemanticColors.auroraCyanBorderSubtle
            : hover.hovered ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle

        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiSpacing.sm
            spacing: MichiSpacing.sm

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: width

                Artwork {
                    anchors.fill: parent
                    sourcePath: root.album && root.album.hasArtwork
                        ? root.album.artworkPath : ""
                    fallbackText: root.album ? root.album.title : "?"
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
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

                Rectangle {
                    anchors.centerIn: parent
                    width: 46
                    height: 46
                    radius: 23
                    visible: hover.hovered || root.activeFocus
                    color: MichiSemanticColors.scrimStrong
                    border.width: 1
                    border.color: MichiSemanticColors.auroraCyanBorder
                    scale: tap.pressed ? 0.94 : 1
                    opacity: hover.hovered || root.activeFocus ? 1 : 0

                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro }
                    }

                    MichiIcon {
                        anchors.centerIn: parent
                        width: 20
                        height: 20
                        name: "play"
                        iconColor: MichiPalette.auroraCyan
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xxs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.sm
                    MichiText {
                        Layout.fillWidth: true
                        text: root.album ? root.album.title : ""
                        role: "body"
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }
                    MichiText {
                        visible: root.album && root.album.year > 0
                        text: root.album ? root.album.year : ""
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.album ? root.album.artist : ""
                    role: "secondary"
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    visible: root.album && root.album.technicalSummary ? (root.album.technicalSummary.length > 0) : false
                    text: root.album && root.album.technicalSummary ? root.album.technicalSummary : ""
                    role: "technical"
                    technical: true
                    color: root.selected ? MichiPalette.auroraCyan : MichiPalette.textMuted
                    elide: Text.ElideRight
                }
                MichiText {
                    Layout.fillWidth: true
                    visible: MichiThemeState.density === "comfortable"
                    text: root.album
                        ? root.album.trackCount
                            + (root.album.trackCount === 1 ? " track" : " tracks")
                        : ""
                    role: "caption"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                }
            }
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
