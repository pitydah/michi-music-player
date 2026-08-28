import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistCard — a personal musical object. Cover/name open the playlist;
// the single centered Play action starts playback without navigation.
Item {
    id: root

    property string playlistId: ""
    property string playlistName: ""
    property int trackCount: 0
    property int durationMs: 0
    property string customCoverPath: ""
    property var mosaicArtworkPaths: []
    property bool pinned: false
    property bool selected: false
    readonly property bool interactionActive: hoverHandler.hovered
        || root.activeFocus || playButton.activeFocus || moreButton.activeFocus
        || contextMenu.visible

    signal openRequested()
    signal playRequested()
    signal pinToggled()
    signal customizeAppearanceRequested()
    signal renameRequested()
    signal deleteRequested()

    implicitWidth: 304
    implicitHeight: 332
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: root.playlistName + ", "
        + MichiFormat.formatPlaylistSummary(root.trackCount, root.durationMs)
    Accessible.description: qsTr("Open playlist")
    Accessible.selected: root.selected

    Keys.onReturnPressed: {
        MichiAccessibility.noteKeyboard()
        root.openRequested()
    }
    Keys.onEnterPressed: {
        MichiAccessibility.noteKeyboard()
        root.openRequested()
    }
    Keys.onSpacePressed: {
        MichiAccessibility.noteKeyboard()
        root.openRequested()
    }

    HoverHandler {
        id: hoverHandler
        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onTapped: function(eventPoint, button) {
            if (button === Qt.RightButton)
                contextMenu.popup()
            else
                root.openRequested()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: root.interactionActive
            ? MichiSemanticColors.surfaceHover : "transparent"
        border.width: 1
        border.color: root.selected && MichiAccessibility.keyboardMode
            ? MichiSemanticColors.auroraCyanBorder
            : root.interactionActive
                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
        MichiFocusRing {
            visualFocus: root.activeFocus && MichiAccessibility.keyboardMode
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        spacing: MichiSpacing.sm

        Item {
            id: artworkStage
            Layout.preferredWidth: 240
            Layout.preferredHeight: width
            Layout.alignment: Qt.AlignLeft

            // Layer order is intentional: background -> cat -> cover ->
            // controls. The revealed portion is the only part not occluded.
            MichiPeek {
                id: michiPeek
                width: 96
                height: 176
                x: artworkStage.width - width
                anchors.verticalCenter: parent.verticalCenter
                revealed: root.interactionActive
                z: 0
            }

            Item {
                id: coverLayer
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width
                x: root.interactionActive && !MichiAccessibility.reducedMotion
                    ? -MichiSpacing.xs : 0
                z: 1

                Behavior on x {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.artwork
                        easing.type: MichiMotion.outCubic
                    }
                }

                PlaylistArtwork {
                    anchors.fill: parent
                    customCoverPath: root.customCoverPath
                    mosaicArtworkPaths: root.mosaicArtworkPaths
                    fallbackText: root.playlistName
                    radius: MichiRadius.lg
                }

                Rectangle {
                    anchors.fill: parent
                    radius: MichiRadius.lg
                    color: root.interactionActive
                        ? MichiSemanticColors.artworkScrimHover : "transparent"
                    Behavior on color {
                        enabled: !MichiAccessibility.reducedMotion
                        ColorAnimation { duration: MichiMotion.micro }
                    }
                }
            }

            MichiButton {
                id: playButton
                anchors.centerIn: coverLayer
                implicitWidth: 52
                implicitHeight: 52
                iconName: "play"
                iconOnly: true
                variant: "primary"
                iconSize: MichiMetrics.iconMedium
                accessibleName: qsTr("Play %1 without opening it").arg(root.playlistName)
                opacity: root.interactionActive ? 1 : 0
                scale: root.interactionActive ? 1 : 0.96
                z: 2
                onClicked: root.playRequested()
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                }
                Behavior on scale {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                }
            }

            MichiIconButton {
                id: moreButton
                anchors.top: coverLayer.top
                anchors.right: coverLayer.right
                anchors.margins: MichiSpacing.sm
                iconName: "more"
                accessibleName: qsTr("More options for %1").arg(root.playlistName)
                opacity: root.interactionActive ? 1 : 0
                z: 2
                onClicked: contextMenu.popup()
                Behavior on opacity {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs
            MichiText {
                Layout.fillWidth: true
                text: root.playlistName
                role: "section"
                elide: Text.ElideRight
                font.weight: Font.DemiBold
            }
            MichiIcon {
                visible: root.pinned
                Layout.preferredWidth: MichiMetrics.iconSmall
                Layout.preferredHeight: MichiMetrics.iconSmall
                name: "pin"
                iconColor: MichiPalette.auroraCyan
                Accessible.role: Accessible.StaticText
                Accessible.name: "Pinned playlist"
            }
        }

        MichiText {
            Layout.fillWidth: true
            text: MichiFormat.formatPlaylistSummary(root.trackCount, root.durationMs)
            role: "technical"
            color: MichiPalette.textMuted
            elide: Text.ElideRight
        }
    }

    MichiMenu {
        id: contextMenu
        MenuItem { text: qsTr("Open"); onTriggered: root.openRequested() }
        MenuItem { text: qsTr("Play now"); onTriggered: root.playRequested() }
        MenuItem {
            text: qsTr("Add to queue")
            onTriggered: playlists.queue_playlist(root.playlistId)
        }
        MenuItem {
            text: root.pinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.pinToggled()
        }
        MenuItem {
            text: qsTr("Customize appearance…")
            onTriggered: root.customizeAppearanceRequested()
        }
        MenuItem { text: qsTr("Rename…"); onTriggered: root.renameRequested() }
        MenuItem { text: qsTr("Delete…"); onTriggered: root.deleteRequested() }
    }
}
