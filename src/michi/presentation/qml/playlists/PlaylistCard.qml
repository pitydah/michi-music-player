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
    signal openRequested()
    signal playRequested()
    signal pinToggled()
    signal renameRequested()
    signal deleteRequested()

    implicitHeight: 220
    implicitWidth: 200
    Accessible.role: Accessible.Button
    Accessible.name: playlistName + ", " + trackCount + " tracks"

    function formatTime(ms) {
        if (!ms || ms <= 0) return ""
        var totalSeconds = Math.round(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        color: rootArea.hovered
            ? MichiSemanticColors.surfaceHover : MichiSemanticColors.contentSurface
        border.width: rootArea.pressed ? 1 : 0
        border.color: MichiSemanticColors.borderSubtle
        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.md
        spacing: MichiSpacing.sm

        PlaylistArtwork {
            Layout.fillWidth: true
            Layout.preferredHeight: width
            customCoverPath: root.customCoverPath
            mosaicArtworkPaths: root.mosaicArtworkPaths
            fallbackText: root.playlistName
            radius: MichiRadius.md
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.xs
                MichiText {
                    text: root.playlistName
                    role: "secondary"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    color: MichiPalette.textPrimary
                    font.weight: Font.DemiBold
                }
                MichiIcon {
                    visible: root.pinned
                    name: "pin"
                    width: 13
                    height: 13
                    iconColor: MichiPalette.auroraCyan
                }
            }

            MichiText {
                text: root.trackCount + (root.trackCount === 1 ? " track" : " tracks")
                    + (root.durationMs > 0 ? " · " + root.formatTime(root.durationMs) : "")
                role: "technical"
                technical: true
                color: MichiPalette.textSecondary
            }
        }
    }

    // M9-R1I keyboard accessibility
    MouseArea {
        id: rootArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        activeFocusOnTab: true
        Keys.onReturnPressed: root.openRequested()
        Keys.onEnterPressed: root.openRequested()
        Keys.onSpacePressed: root.openRequested()
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton)
                contextMenu.popup()
            else
                root.openRequested()
        }
    }

    // Visible focus state
    Rectangle {
        anchors.fill: parent
        radius: MichiRadius.lg
        visible: rootArea.activeFocus
        border.width: 1
        border.color: MichiPalette.auroraCyan
        color: "transparent"
        z: 2
    }

    RowLayout {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: MichiSpacing.md
        anchors.rightMargin: MichiSpacing.md
        spacing: MichiSpacing.xs
        z: 3

        MichiIconButton {
            iconName: "play"
            accessibleName: qsTr("Play ") + root.playlistName
            onClicked: root.playRequested()
        }
        MichiIconButton {
            iconName: root.pinned ? "pin" : "circle"
            accessibleName: root.pinned
                ? qsTr("Unpin ") + root.playlistName
                : qsTr("Pin ") + root.playlistName
            onClicked: root.pinToggled()
        }
        MichiIconButton {
            iconName: "sliders"
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
            text: qsTr("Play")
            onTriggered: root.playRequested()
        }
        MenuItem {
            text: qsTr("Add to Queue")
            onTriggered: playlists.queue_playlist(root.playlistId)
        }
        MenuItem {
            text: root.pinned ? qsTr("Unpin") : qsTr("Pin")
            onTriggered: root.pinToggled()
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
