import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property var album: null
    signal activated()

    implicitHeight: Math.max(MichiThemeState.rowHeight, 44)
    radius: MichiRadius.sm
    color: hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: root.album
        ? root.album.title + " by " + root.album.artist
        : "Album"

    Keys.onEnterPressed: root.activated()
    Keys.onReturnPressed: root.activated()
    Keys.onSpacePressed: root.activated()

    function formatDuration(ms) {
        if (ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        Artwork {
            Layout.preferredWidth: 34
            Layout.preferredHeight: 34
            sourcePath: root.album && root.album.hasArtwork ? root.album.artworkPath : ""
            fallbackText: root.album ? root.album.title : "?"
            requestedSize: 72
        }

        MichiText {
            Layout.fillWidth: true
            text: root.album ? root.album.title : ""
            role: "body"
            elide: Text.ElideRight
        }
        MichiText {
            Layout.preferredWidth: 170
            text: root.album ? root.album.artist : ""
            role: "secondary"
            elide: Text.ElideRight
        }
        MichiText {
            text: root.album && root.album.year > 0 ? root.album.year : ""
            role: "technical"
            technical: true
        }
        MichiText {
            text: root.album ? root.formatDuration(root.album.durationMs) : ""
            role: "technical"
            technical: true
        }
        MichiText {
            Layout.preferredWidth: 150
            visible: MichiThemeState.precisionMode
            text: root.album ? root.album.technicalSummary : ""
            role: "technical"
            technical: true
            color: MichiPalette.auroraCyan
            elide: Text.ElideRight
        }
    }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler {
        onTapped: {
            root.forceActiveFocus()
            root.activated()
        }
    }
    MichiFocusRing { visualFocus: root.activeFocus }
}
