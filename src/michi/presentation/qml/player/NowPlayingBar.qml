import QtQuick
import QtQuick.Controls.Basic
import "../controls"
import "../media"
import "../primitives"
import "../theme"

Item {
    id: root
    objectName: "nowPlayingBar"

    property string trackTitle: ""
    property string artist: ""
    property string qualityLabel: ""
    property string formatLabel: ""
    property string artworkPath: ""
    property string status: "stopped"
    property int position: 0
    property int duration: 0
    property int volume: 100
    property bool muted: false
    property bool hasPrevious: false
    property bool hasNext: false
    property bool shuffleEnabled: false
    property string repeatMode: "NONE"

    readonly property bool hasTrack: trackTitle.length > 0
    readonly property int transportOrigin: Math.round(width / 2 - 177)

    signal playPauseRequested()
    signal previousRequested()
    signal nextRequested()
    signal seekRequested(int seconds)
    signal volumeRequested(int value)
    signal muteRequested(bool muted)
    signal shuffleRequested(bool enabled)
    signal repeatRequested(string mode)
    signal queueRequested()
    signal settingsRequested()
    signal nowPlayingRequested()

    implicitWidth: 1920
    implicitHeight: 154
    clip: true

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.backplane
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }

    Rectangle {
        id: trackCard
        objectName: "trackCard"
        x: 38
        y: 34
        width: 270
        height: 86
        radius: 17
        color: MichiSemanticColors.controlSurface
        border.width: 1
        border.color: Qt.rgba(0.604, 0.486, 1, 0.24)

        Artwork {
            objectName: "trackArtwork"
            x: 12
            y: 12
            width: 64
            height: 64
            radius: 11
            sourcePath: root.artworkPath
            fallbackText: root.trackTitle.length > 0 ? root.trackTitle : "M"
        }

        MichiText {
            x: 90
            y: 15
            width: 162
            height: 21
            text: root.hasTrack ? root.trackTitle : "No track selected"
            role: "body"
            font.weight: Font.DemiBold
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        MichiText {
            x: 90
            y: 39
            width: 162
            height: 18
            text: root.hasTrack ? (root.artist.length > 0 ? root.artist : "Unknown artist") : "Add music"
            role: "secondary"
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        MichiText {
            x: 90
            y: 60
            width: 162
            height: 15
            text: root.qualityLabel.length > 0 ? root.qualityLabel : outputText()
            role: "caption"
            color: MichiPalette.textMuted
            font.capitalization: Font.AllUppercase
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }

        TapHandler { onTapped: root.nowPlayingRequested() }
    }

    MichiText {
        id: elapsedLabel
        objectName: "elapsedLabel"
        x: 340
        y: 39
        width: 34
        height: 16
        text: formatTime(root.position)
        role: "technical"
        technical: true
        color: MichiPalette.textPrimary
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
    }

    Slider {
        id: timeline
        objectName: "timeline"
        x: 385
        y: 33
        width: Math.max(40, root.width - 758)
        height: 28
        from: 0
        to: Math.max(root.duration, 1)
        value: Math.min(root.position, to)
        enabled: root.duration > 0
        focusPolicy: Qt.StrongFocus
        Accessible.role: Accessible.Slider
        Accessible.name: "Playback position"
        Accessible.description: formatTime(value) + " of " + formatTime(root.duration)
        onMoved: root.seekRequested(Math.round(value))

        background: Rectangle {
            x: timeline.leftPadding
            y: timeline.topPadding + timeline.availableHeight / 2 - height / 2
            width: timeline.availableWidth
            height: 8
            radius: 4
            color: MichiPalette.smokeRaised
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle

            Rectangle {
                width: timeline.visualPosition * parent.width
                height: parent.height
                radius: parent.radius
                color: timeline.enabled ? MichiPalette.auroraBlue : MichiPalette.textDisabled
                Rectangle {
                    anchors.right: parent.right
                    width: Math.min(parent.width, 120)
                    height: parent.height
                    radius: parent.radius
                    color: MichiPalette.auroraPurple
                    opacity: parent.width > 24 ? 0.74 : 0
                }
            }
        }
        handle: Rectangle {
            x: timeline.leftPadding + timeline.visualPosition * (timeline.availableWidth - width)
            y: timeline.topPadding + timeline.availableHeight / 2 - height / 2
            width: 18
            height: 18
            radius: 9
            color: MichiPalette.textPrimary
            border.width: 2
            border.color: timeline.pressed || timeline.visualFocus
                ? MichiPalette.auroraCyan : MichiPalette.auroraPurple
            scale: timeline.pressed ? 1.08 : 1
            Behavior on scale {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation { duration: MichiMotion.micro }
            }
            MichiFocusRing { visualFocus: timeline.visualFocus }
        }
    }

    MichiText {
        objectName: "remainingLabel"
        x: root.width - 348
        y: 39
        width: 40
        height: 16
        text: formatTime(root.duration)
        role: "technical"
        technical: true
        color: MichiPalette.textPrimary
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    MichiIconButton {
        objectName: "shuffleButton"
        x: root.transportOrigin
        y: 82
        width: 36
        height: 36
        iconName: "shuffle"
        accessibleName: root.shuffleEnabled ? "Disable shuffle" : "Enable shuffle"
        selected: root.shuffleEnabled
        enabled: root.hasTrack
        onClicked: root.shuffleRequested(!root.shuffleEnabled)
    }
    MichiIconButton {
        objectName: "previousButton"
        x: root.transportOrigin + 55
        y: 82
        width: 36
        height: 36
        iconName: "previous"
        accessibleName: "Previous track"
        enabled: root.hasPrevious
        onClicked: root.previousRequested()
    }

    Button {
        id: playPauseButton
        objectName: "playPauseButton"
        x: root.transportOrigin + 106
        y: 73
        width: 55
        height: 54
        enabled: root.hasTrack
        focusPolicy: Qt.StrongFocus
        hoverEnabled: true
        Accessible.role: Accessible.Button
        Accessible.name: root.status === "playing" ? "Pause" : "Play"
        onClicked: root.playPauseRequested()

        contentItem: MichiIcon {
            anchors.centerIn: parent
            width: 28
            height: 28
            name: root.status === "playing" ? "pause" : "play"
            iconColor: playPauseButton.enabled ? MichiPalette.auroraCyan : MichiPalette.textDisabled
            strokeWidth: 2
        }
        background: Rectangle {
            radius: 17
            color: playPauseButton.pressed ? MichiSemanticColors.surfacePressed
                : playPauseButton.hovered ? MichiSemanticColors.surfaceHover
                : MichiPalette.smoke
            border.width: 1
            border.color: playPauseButton.visualFocus
                ? MichiSemanticColors.focusRing : MichiSemanticColors.borderStrong
            MichiFocusRing { visualFocus: playPauseButton.visualFocus }
        }
        MichiTooltip {
            visible: playPauseButton.hovered
            text: playPauseButton.Accessible.name
        }
    }

    MichiIconButton {
        objectName: "nextButton"
        x: root.transportOrigin + 177
        y: 82
        width: 36
        height: 36
        iconName: "next"
        accessibleName: "Next track"
        enabled: root.hasNext
        onClicked: root.nextRequested()
    }
    MichiIconButton {
        objectName: "repeatButton"
        x: root.transportOrigin + 230
        y: 82
        width: 36
        height: 36
        iconName: root.repeatMode === "ONE" ? "repeat-one" : "repeat"
        accessibleName: "Repeat: " + root.repeatMode.toLowerCase()
        selected: root.repeatMode !== "NONE"
        enabled: root.hasTrack
        onClicked: root.repeatRequested(nextRepeatMode(root.repeatMode))
    }

    MichiIconButton {
        objectName: "outputStatusButton"
        x: root.width - 414
        y: 82
        width: 36
        height: 36
        iconName: "device"
        accessibleName: "Local audio output"
        enabled: false
    }
    MichiIconButton {
        objectName: "queueButton"
        x: root.width - 360
        y: 82
        width: 36
        height: 36
        iconName: "queue"
        accessibleName: "Open queue"
        onClicked: root.queueRequested()
    }

    MichiIconButton {
        objectName: "muteButton"
        x: root.width - 295
        y: 33
        width: 36
        height: 36
        iconName: root.muted || root.volume === 0 ? "mute" : "volume"
        accessibleName: root.muted ? "Unmute" : "Mute"
        onClicked: root.muteRequested(!root.muted)
    }
    Slider {
        id: volumeSlider
        objectName: "volumeSlider"
        x: root.width - 240
        y: 33
        width: 80
        height: 28
        from: 0
        to: 100
        value: root.volume
        focusPolicy: Qt.StrongFocus
        Accessible.role: Accessible.Slider
        Accessible.name: "Volume"
        Accessible.description: Math.round(value) + " percent"
        onMoved: root.volumeRequested(Math.round(value))

        background: Rectangle {
            y: volumeSlider.availableHeight / 2 - height / 2
            width: volumeSlider.availableWidth
            height: 7
            radius: 4
            color: MichiPalette.smokeRaised
            Rectangle {
                width: volumeSlider.visualPosition * parent.width
                height: parent.height
                radius: parent.radius
                color: MichiPalette.auroraBlue
            }
        }
        handle: Rectangle {
            x: volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
            y: volumeSlider.availableHeight / 2 - height / 2
            width: 16
            height: 16
            radius: 8
            color: MichiPalette.textPrimary
            border.width: 2
            border.color: volumeSlider.visualFocus
                ? MichiPalette.auroraCyan : MichiPalette.auroraPurple
            MichiFocusRing { visualFocus: volumeSlider.visualFocus }
        }
    }
    MichiIconButton {
        objectName: "settingsButton"
        x: root.width - 132
        y: 33
        width: 36
        height: 36
        iconName: "sliders"
        accessibleName: "Audio settings"
        onClicked: root.settingsRequested()
    }
    MichiIconButton {
        objectName: "deviceButton"
        x: root.width - 80
        y: 33
        width: 36
        height: 36
        iconName: "device"
        accessibleName: "Output selection unavailable"
        enabled: false
    }

    Rectangle {
        id: outputBadge
        objectName: "outputBadge"
        x: root.width - 198
        y: 86
        width: 150
        height: 34
        radius: 13
        color: Qt.rgba(0.604, 0.486, 1, 0.10)
        border.width: 1
        border.color: Qt.rgba(0.604, 0.486, 1, 0.30)

        Row {
            anchors.centerIn: parent
            spacing: 6
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 8
                height: 8
                radius: 4
                color: root.hasTrack ? MichiPalette.auroraGreen : MichiPalette.textMuted
            }
            MichiText {
                anchors.verticalCenter: parent.verticalCenter
                text: outputText()
                role: "technical"
                technical: true
                color: MichiPalette.textPrimary
                font.weight: Font.DemiBold
            }
        }
    }

    function formatTime(seconds) {
        var safe = Math.max(0, Math.floor(seconds))
        var minutes = Math.floor(safe / 60)
        var remainder = safe % 60
        return minutes + ":" + (remainder < 10 ? "0" : "") + remainder
    }

    function outputText() {
        return root.formatLabel.length > 0 ? "LOCAL · " + root.formatLabel : "LOCAL"
    }

    function nextRepeatMode(mode) {
        if (mode === "NONE") return "ALL"
        if (mode === "ALL") return "ONE"
        return "NONE"
    }
}
