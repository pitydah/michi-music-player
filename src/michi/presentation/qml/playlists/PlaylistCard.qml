import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistCard — quiet content surface (glass = controls). Primary click
// opens the playlist; play affordance routes through PlaylistService →
// QueueService; pin toggles; overflow opens the context menu.
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
    signal openRequested()
    signal playRequested()
    signal pinToggled()
    signal changeCoverRequested()
    signal renameRequested()
    signal deleteRequested()

    implicitHeight: 220
    implicitWidth: 200
    focus: false
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: playlistName + ", " + trackCount + " tracks"

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

    function formatTime(ms) {
        if (!ms || ms <= 0) return ""
        var totalSeconds = Math.round(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    HoverHandler { id: hoverHandler }
    TapHandler {
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onTapped: function(eventPoint, button) {
            if (button === Qt.RightButton) {
                contextMenu.popup()
            } else {
                root.openRequested()
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: hoverHandler.hovered
            ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
        border.width: root.selected ? 1 : 1
        border.color: root.selected
            ? MichiSemanticColors.auroraCyanBorder
            : hoverHandler.hovered
                ? MichiSemanticColors.borderStrong : MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }

    // Keyboard-current indicator (grid arrow-key navigation)
    Rectangle {
        visible: root.selected
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - MichiSpacing.xl * 2, 32)
        height: 2
        radius: 1
        color: MichiPalette.auroraCyan
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        spacing: MichiSpacing.sm

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: width

            // Vinyl Record peeking out to the right on hover
            Rectangle {
                id: vinylDisc
                anchors.verticalCenter: parent.verticalCenter
                x: hoverHandler.hovered ? parent.width * 0.16 : 0
                width: parent.width * 0.94
                height: width
                radius: width / 2
                color: MichiPalette.obsidianDeep
                border.width: 1
                border.color: MichiSemanticColors.borderStrong
                z: 0

                // Grooves
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.72
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.width: 1
                    border.color: MichiPalette.graphite
                }

                // Center Label
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.34
                    height: width
                    radius: width / 2
                    color: MichiPalette.auroraBlue
                    opacity: 0.85
                    Rectangle {
                        anchors.centerIn: parent
                        width: 6
                        height: 6
                        radius: 3
                        color: MichiPalette.obsidian
                    }
                }

                Behavior on x {
                    enabled: !MichiAccessibility.reducedMotion
                    NumberAnimation {
                        duration: MichiMotion.standard
                        easing.type: MichiMotion.outCubic
                    }
                }
            }

            PlaylistArtwork {
                anchors.fill: parent
                customCoverPath: root.customCoverPath
                mosaicArtworkPaths: root.mosaicArtworkPaths
                fallbackText: root.playlistName
                radius: MichiRadius.md
                z: 1
            }

            // Quick Play Button Overlay on Hover
            Rectangle {
                anchors.centerIn: parent
                width: 44
                height: 44
                radius: 22
                color: MichiSemanticColors.scrimStrong
                border.width: 1
                border.color: MichiSemanticColors.auroraCyanBorder
                visible: hoverHandler.hovered
                z: 2

                MichiIcon {
                    name: "play"
                    width: 20
                    height: 20
                    anchors.centerIn: parent
                    iconColor: MichiPalette.auroraCyan
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.playRequested()
                }
            }
        }

        MichiText {
            text: root.playlistName
            role: "cardTitle"
            elide: Text.ElideRight
            font.weight: Font.DemiBold
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xs

            MichiText {
                text: root.trackCount + (root.trackCount === 1 ? " track" : " tracks")
                    + (root.durationMs > 0 ? " · " + root.formatTime(root.durationMs) : "")
                role: "secondary"
                elide: Text.ElideRight
                color: MichiPalette.textSecondary
                Layout.fillWidth: true
            }

            Rectangle {
                visible: root.pinned
                width: 6
                height: 6
                radius: 3
                color: MichiPalette.auroraCyan
            }
        }
    }

    // Hover quick actions (desktop quietness: only visible on card hover)
    RowLayout {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiSpacing.sm
        spacing: MichiSpacing.xs
        visible: hoverHandler.hovered

        MichiIconButton {
            iconName: "play"
            accessibleName: qsTr("Play ") + root.playlistName
            onClicked: root.playRequested()
        }

        MichiIconButton {
            iconName: "more"
            accessibleName: qsTr("More options for ") + root.playlistName
            onClicked: contextMenu.popup()
        }
    }

    MichiMenu {
        id: contextMenu
        MenuItem {
            text: qsTr("Open")
            onTriggered: root.openRequested()
        }
        MenuItem {
            text: qsTr("Play Now")
            onTriggered: root.playRequested()
        }
        MenuItem {
            text: qsTr("Add to Queue")
            onTriggered: playlists.enqueue_playlist(root.playlistId)
        }
        MenuItem {
            text: root.pinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.pinToggled()
        }
        MenuItem {
            text: qsTr("Change Cover…")
            onTriggered: root.changeCoverRequested()
        }
        MenuItem {
            text: qsTr("Use Automatic Mosaic")
            visible: (root.customCoverPath || "") !== ""
            onTriggered: playlists.remove_custom_cover(root.playlistId)
        }
        MenuItem {
            text: qsTr("Rename")
            onTriggered: root.renameRequested()
        }
        MenuItem {
            text: qsTr("Delete")
            onTriggered: root.deleteRequested()
        }
    }
}
