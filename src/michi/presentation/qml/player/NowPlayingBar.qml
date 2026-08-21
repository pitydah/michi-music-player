import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

Item {
    id: root
    objectName: "nowPlayingBar"

    property string trackTitle: ""
    property string artist: ""
    property string album: ""
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
    readonly property bool compact: width < 1320
    readonly property bool narrow: width < 980
    readonly property int horizontalInset: compact ? 20 : 38
    readonly property int sliderTrackHeight: 6

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

    implicitWidth: 800
    implicitHeight: 154
    clip: true

    Rectangle {
        anchors.fill: parent
        color: MichiSemanticColors.backplane
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiPalette.playerSurfaceTop }
            GradientStop { position: 1; color: MichiPalette.obsidianDeep }
        }
        border.width: 1
        border.color: MichiSemanticColors.borderSubtle
    }

    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.max(240, parent.width * 0.42)
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.5; color: MichiSemanticColors.auroraBlueGlow }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.horizontalInset
        anchors.rightMargin: root.horizontalInset
        anchors.topMargin: 20
        anchors.bottomMargin: 20
        spacing: root.compact ? 16 : 30

        Rectangle {
            id: trackCard
            objectName: "trackCard"
            Layout.preferredWidth: root.narrow ? 82 : root.compact ? 220 : 270
            Layout.minimumWidth: root.narrow ? 72 : 184
            Layout.maximumWidth: 270
            Layout.preferredHeight: 86
            Layout.alignment: Qt.AlignVCenter
            radius: 17
            color: MichiSemanticColors.controlSurface
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop {
                    position: 0
                    color: trackHover.hovered
                        ? MichiPalette.trackSurfaceHover : MichiPalette.trackSurfaceTop
                }
                GradientStop { position: 1; color: MichiPalette.trackSurfaceBottom }
            }
            border.width: 1
            border.color: trackHover.hovered
                ? MichiSemanticColors.auroraCyanBorderStrong
                : MichiSemanticColors.auroraPurpleBorderSoft

            RowLayout {
                anchors.fill: parent
                anchors.margins: 11
                spacing: 14

                Artwork {
                    objectName: "trackArtwork"
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 64
                    Layout.alignment: Qt.AlignVCenter
                    radius: 11
                    sourcePath: root.artworkPath
                    fallbackText: root.trackTitle.length > 0 ? root.trackTitle : "M"
                }

                ColumnLayout {
                    visible: !root.narrow
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0

                    MichiText {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 24
                        text: root.hasTrack ? root.trackTitle : "No track selected"
                        role: "body"
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    MichiText {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 20
                        text: root.hasTrack
                            ? (root.artist.length > 0 ? root.artist : "Unknown artist")
                            : "Add music"
                        role: "secondary"
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    MichiText {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 18
                        text: root.hasTrack
                            ? (root.album.length > 0 ? root.album : "Unknown album")
                            : "Local library"
                        role: "caption"
                        color: MichiPalette.textMuted
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            TapHandler { onTapped: root.nowPlayingRequested() }
            HoverHandler { id: trackHover; cursorShape: Qt.PointingHandCursor }
            Behavior on border.color {
                enabled: !MichiAccessibility.reducedMotion
                ColorAnimation { duration: MichiMotion.micro }
            }
        }

        ColumnLayout {
            id: playbackZone
            objectName: "playbackZone"
            Layout.fillWidth: true
            Layout.minimumWidth: 360
            Layout.fillHeight: true
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                spacing: 10

                MichiText {
                    id: elapsedLabel
                    objectName: "elapsedLabel"
                    Layout.preferredWidth: 36
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
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
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
                        height: root.sliderTrackHeight
                        radius: height / 2
                        color: MichiPalette.smokeRaised
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle

                        Rectangle {
                            width: timeline.visualPosition * parent.width
                            height: parent.height
                            radius: parent.radius
                            color: timeline.enabled
                                ? MichiPalette.auroraBlue : MichiPalette.textDisabled
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: MichiPalette.auroraBlue }
                                GradientStop { position: 0.72; color: MichiPalette.auroraCyan }
                                GradientStop { position: 1; color: MichiPalette.auroraPurple }
                            }
                        }
                    }
                    handle: Rectangle {
                        x: timeline.leftPadding
                            + timeline.visualPosition * (timeline.availableWidth - width)
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
                    Layout.preferredWidth: 40
                    text: formatTime(root.duration)
                    role: "technical"
                    technical: true
                    color: MichiPalette.textPrimary
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                RowLayout {
                    anchors.centerIn: parent
                    spacing: root.compact ? 7 : 15

                    MichiIconButton {
                        objectName: "shuffleButton"
                        iconName: "shuffle"
                        accessibleName: root.shuffleEnabled
                            ? "Disable shuffle" : "Enable shuffle"
                        selected: root.shuffleEnabled
                        enabled: root.hasTrack
                        onClicked: root.shuffleRequested(!root.shuffleEnabled)
                    }
                    MichiIconButton {
                        objectName: "previousButton"
                        iconName: "previous"
                        accessibleName: "Previous track"
                        enabled: root.hasPrevious
                        onClicked: root.previousRequested()
                    }

                    Button {
                        id: playPauseButton
                        objectName: "playPauseButton"
                        Layout.preferredWidth: 55
                        Layout.preferredHeight: 54
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
                            iconColor: playPauseButton.enabled
                                ? MichiPalette.auroraCyan : MichiPalette.textDisabled
                            strokeWidth: 2
                        }
                        background: Rectangle {
                            radius: 17
                            color: playPauseButton.pressed
                                ? MichiSemanticColors.surfacePressed
                                : playPauseButton.hovered
                                    ? MichiSemanticColors.surfaceHover : MichiPalette.smoke
                            border.width: 1
                            border.color: playPauseButton.visualFocus
                                ? MichiSemanticColors.focusRing
                                : MichiSemanticColors.borderStrong
                            scale: playPauseButton.pressed ? 0.96
                                : playPauseButton.hovered ? 1.025 : 1
                            Behavior on scale {
                                enabled: !MichiAccessibility.reducedMotion
                                NumberAnimation {
                                    duration: MichiMotion.micro
                                    easing.type: MichiMotion.outCubic
                                }
                            }
                            MichiFocusRing { visualFocus: playPauseButton.visualFocus }
                        }
                        MichiTooltip {
                            visible: playPauseButton.hovered
                            text: playPauseButton.Accessible.name
                        }
                    }

                    MichiIconButton {
                        objectName: "nextButton"
                        iconName: "next"
                        accessibleName: "Next track"
                        enabled: root.hasNext
                        onClicked: root.nextRequested()
                    }
                    MichiIconButton {
                        objectName: "repeatButton"
                        iconName: root.repeatMode === "ONE" ? "repeat-one" : "repeat"
                        accessibleName: "Repeat: " + root.repeatMode.toLowerCase()
                        selected: root.repeatMode !== "NONE"
                        enabled: root.hasTrack
                        onClicked: root.repeatRequested(nextRepeatMode(root.repeatMode))
                    }
                }
            }
        }

        ColumnLayout {
            id: outputZone
            objectName: "outputZone"
            Layout.preferredWidth: root.compact ? 248 : 286
            Layout.minimumWidth: 224
            Layout.maximumWidth: 300
            Layout.fillHeight: true
            spacing: 8

            RowLayout {
                objectName: "volumeControlRow"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                spacing: MichiSpacing.xs

                MichiIconButton {
                    objectName: "muteButton"
                    iconName: root.muted || root.volume === 0 ? "mute" : "volume"
                    accessibleName: root.muted ? "Unmute" : "Mute"
                    onClicked: root.muteRequested(!root.muted)
                }
                Slider {
                    id: volumeSlider
                    objectName: "volumeSlider"
                    Layout.fillWidth: true
                    Layout.minimumWidth: 72
                    Layout.preferredHeight: 28
                    from: 0
                    to: 100
                    value: root.volume
                    focusPolicy: Qt.StrongFocus
                    hoverEnabled: true
                    Accessible.role: Accessible.Slider
                    Accessible.name: "Volume"
                    Accessible.description: Math.round(value) + " percent"
                    onMoved: root.volumeRequested(Math.round(value))

                    background: Rectangle {
                        y: volumeSlider.availableHeight / 2 - height / 2
                        width: volumeSlider.availableWidth
                        height: root.sliderTrackHeight
                        radius: height / 2
                        color: MichiPalette.smokeRaised
                        border.width: 1
                        border.color: MichiSemanticColors.borderSubtle
                        Rectangle {
                            width: volumeSlider.visualPosition * parent.width
                            height: parent.height
                            radius: parent.radius
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: MichiPalette.auroraBlue }
                                GradientStop { position: 0.72; color: MichiPalette.auroraCyan }
                                GradientStop { position: 1; color: MichiPalette.auroraPurple }
                            }
                        }
                    }
                    handle: Rectangle {
                        x: volumeSlider.visualPosition
                            * (volumeSlider.availableWidth - width)
                        y: volumeSlider.availableHeight / 2 - height / 2
                        width: 14
                        height: 14
                        radius: 7
                        color: MichiPalette.textPrimary
                        border.width: 2
                        border.color: volumeSlider.visualFocus
                            || volumeSlider.hovered
                            ? MichiPalette.auroraCyan : MichiPalette.auroraPurple
                        Rectangle {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: MichiSemanticColors.auroraCyanBorder
                            visible: volumeSlider.hovered
                                || volumeSlider.pressed || volumeSlider.visualFocus
                        }
                        MichiFocusRing { visualFocus: volumeSlider.visualFocus }
                    }
                }
                MichiText {
                    visible: !root.compact
                    Layout.preferredWidth: 30
                    text: Math.round(volumeSlider.value) + "%"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    horizontalAlignment: Text.AlignRight
                }
                MichiIconButton {
                    objectName: "settingsButton"
                    iconName: "sliders"
                    accessibleName: "Audio settings"
                    onClicked: root.settingsRequested()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                Item { Layout.fillWidth: true }

                MichiIconButton {
                    objectName: "queueButton"
                    iconName: "queue"
                    accessibleName: "Open queue"
                    onClicked: root.queueRequested()
                }

                Rectangle {
                    id: qualityBadge
                    objectName: "qualityBadge"
                    Layout.preferredWidth: root.compact ? 156 : 190
                    Layout.preferredHeight: 34
                    radius: 13
                    color: MichiSemanticColors.auroraPurpleSurfaceSoft
                    border.width: 1
                    border.color: MichiSemanticColors.auroraPurpleBorderMedium
                    Accessible.role: Accessible.StaticText
                    Accessible.name: "File quality: " + root.qualityText()

                    Row {
                        anchors.centerIn: parent
                        spacing: MichiSpacing.xs
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 2
                            height: 14
                            radius: 1
                            gradient: Gradient {
                                GradientStop { position: 0; color: MichiPalette.auroraCyan }
                                GradientStop { position: 1; color: MichiPalette.auroraPurple }
                            }
                        }
                        MichiText {
                            anchors.verticalCenter: parent.verticalCenter
                            width: qualityBadge.width - MichiSpacing.xl * 2
                            text: root.qualityText()
                            role: "technical"
                            technical: true
                            color: MichiPalette.textPrimary
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    function formatTime(seconds) {
        var safe = Math.max(0, Math.floor(seconds))
        var minutes = Math.floor(safe / 60)
        var remainder = safe % 60
        return minutes + ":" + (remainder < 10 ? "0" : "") + remainder
    }

    function qualityText() {
        if (root.qualityLabel.length > 0)
            return root.qualityLabel
        if (root.formatLabel.length > 0)
            return root.formatLabel
        return root.hasTrack ? "QUALITY —" : "NO TRACK"
    }

    function nextRepeatMode(mode) {
        if (mode === "NONE") return "ALL"
        if (mode === "ALL") return "ONE"
        return "NONE"
    }
}
