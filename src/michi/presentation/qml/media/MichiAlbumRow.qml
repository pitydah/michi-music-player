import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root

    property var album: null
    property bool selected: false
    property bool showArtist: true
    property bool showYear: true
    property bool showTrackCount: true
    property bool showDuration: true
    property bool showTechnical: MichiThemeState.precisionMode
    signal activated()

    implicitHeight: Math.max(MichiThemeState.rowHeight, 44)
    radius: MichiRadius.sm
    color: root.selected ? MichiSemanticColors.surfaceSelected
        : hover.hovered ? MichiSemanticColors.surfaceHover : "transparent"
    border.width: root.selected || hover.hovered ? 1 : 0
    border.color: root.selected
        ? MichiSemanticColors.auroraBorderSubtle : MichiSemanticColors.borderSubtle
    activeFocusOnTab: true
    Accessible.role: Accessible.ListItem
    Accessible.name: root.album
        ? root.album.title + " by " + root.album.artist
        : "Album"
    Accessible.description: "Open album"

    Keys.onEnterPressed: root.activated()
    Keys.onReturnPressed: root.activated()
    Keys.onSpacePressed: root.activated()

    function formatDuration(ms) {
        if (ms <= 0)
            return ""
        var totalSeconds = Math.floor(ms / 1000)
        var hours = Math.floor(totalSeconds / 3600)
        var minutes = Math.floor((totalSeconds % 3600) / 60)
        var seconds = totalSeconds % 60
        if (hours > 0)
            return hours + ":" + (minutes < 10 ? "0" : "") + minutes
                + ":" + (seconds < 10 ? "0" : "") + seconds
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.sm
        anchors.rightMargin: MichiSpacing.sm
        spacing: MichiSpacing.md

        Artwork {
            Layout.preferredWidth: MichiThemeState.density === "comfortable" ? 40 : 34
            Layout.preferredHeight: Layout.preferredWidth
            sourcePath: root.album && root.album.hasArtwork ? root.album.artworkPath : ""
            fallbackText: root.album ? root.album.title : "?"
            requestedSize: Math.round(width * Screen.devicePixelRatio)
        }

        MichiText {
            Layout.fillWidth: true
            text: root.album ? root.album.title : ""
            role: "body"
            font.weight: root.selected ? Font.DemiBold : Font.Medium
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showArtist
            Layout.preferredWidth: 170
            Layout.minimumWidth: 96
            text: root.album ? root.album.artist : ""
            role: "secondary"
            elide: Text.ElideRight
        }
        MichiText {
            visible: root.showYear
            Layout.preferredWidth: 54
            text: root.album && root.album.year > 0 ? root.album.year : "—"
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
            color: root.album && root.album.year > 0
                ? MichiPalette.textSecondary : MichiPalette.textMuted
        }
        MichiText {
            visible: root.showTrackCount
            Layout.preferredWidth: 48
            text: root.album ? root.album.trackCount : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showDuration
            Layout.preferredWidth: 58
            text: root.album ? root.formatDuration(root.album.durationMs) : ""
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignRight
        }
        MichiText {
            visible: root.showTechnical
            Layout.preferredWidth: 160
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
    MichiFocusRing {
        visualFocus: root.activeFocus && MichiAccessibility.keyboardMode
    }
    Behavior on color {
        enabled: !MichiAccessibility.reducedMotion
        ColorAnimation { duration: MichiMotion.micro }
    }
}
