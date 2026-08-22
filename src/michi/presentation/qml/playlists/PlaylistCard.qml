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
    signal changeCoverRequested()
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

        MichiText {
            text: root.playlistName
            role: "cardTitle"
            elide: Text.ElideRight
            Layout.fillWidth: true
            color: MichiPalette.textPrimary
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

    MouseArea {
        id: rootArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton) {
                contextMenu.popup()
            } else {
                root.openRequested()
            }
        }
    }

    // Hover quick actions (desktop quietness: only visible on card hover)
    RowLayout {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiSpacing.sm
        spacing: MichiSpacing.xs
        visible: rootArea.hovered

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
