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
    property bool showRemainingTime: false
    // M11.3-UI: quick engine selection projections (bound from AppShell).
    property var audioEngines: []
    property string selectedEngineId: ""
    property string activeEngineId: ""
    property string audioEngineActiveName: ""
    property string audioEngineSelectedName: ""
    property string audioEngineLifecycle: ""
    property string audioEngineSwitchingTo: ""
    property string audioEngineFallbackFrom: ""
    property string audioEngineStatusSummary: ""
    property bool audioEngineSwitchReady: true
    property string audioEngineSwitchBlocker: ""
    // PLAYBACK-CONTROLS-R1 (P2): the Play affordance derives from MEDIA
    // truth (committed logical track), not from presentation text.
    property string currentPath: ""
    readonly property bool hasPlayableMedia: root.currentPath !== ""
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
    signal audioEngineSwitchRequested(string engineId)
    signal audioEngineRefreshRequested()

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

    // The bar is the app's most visible surface — it shares the premium
    // film-grain material with the rest of the glass (fixed seed).
    MichiMaterialTexture {
        anchors.fill: parent
        tileSeed: 17
        visible: !MichiAccessibility.highContrast
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

        MichiGlassSurface {
            id: trackCard
            objectName: "trackCard"
            Layout.preferredWidth: root.narrow ? 88 : root.compact ? 252 : 326
            Layout.minimumWidth: root.narrow ? 76 : 204
            Layout.maximumWidth: 334
            Layout.preferredHeight: 94
            Layout.alignment: Qt.AlignVCenter
            elevation: trackHover.hovered ? "elevated" : "standard"
            contentPadding: 0
            shadowed: true
            textured: true
            accented: root.hasTrack
            accentColor: MichiPalette.auroraCyan
            radius: 17

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 14

                Artwork {
                    objectName: "trackArtwork"
                    Layout.preferredWidth: 72
                    Layout.preferredHeight: 72
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
                        role: "secondary"
                        color: MichiPalette.textSecondary
                        opacity: 0.7
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            TapHandler { onTapped: root.nowPlayingRequested() }
            HoverHandler { id: trackHover; cursorShape: Qt.PointingHandCursor }
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
                    hoverEnabled: true
                    Accessible.role: Accessible.Slider
                    Accessible.name: qsTr("Playback position")
                    Accessible.description: qsTr("%1 of %2")
                        .arg(formatTime(value))
                        .arg(formatTime(root.duration))
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
                            ? MichiPalette.auroraCyan
                            : timeline.hovered ? MichiPalette.auroraBlue : MichiPalette.auroraPurple
                        scale: timeline.pressed ? 1.08 : timeline.hovered ? 1.04 : 1
                        Behavior on scale {
                            enabled: !MichiAccessibility.reducedMotion
                            NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                        }
                        MichiFocusRing { visualFocus: timeline.visualFocus }
                    }
                }

                MichiText {
                    id: remainingLabel
                    objectName: "remainingLabel"
                    Layout.preferredWidth: 44
                    text: root.showRemainingTime && root.duration > 0
                        ? ("-" + formatTime(Math.max(0, root.duration - root.position)))
                        : formatTime(root.duration)
                    role: "technical"
                    technical: true
                    color: remHover.hovered ? MichiPalette.auroraCyan : MichiPalette.textPrimary
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    HoverHandler { id: remHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: root.showRemainingTime = !root.showRemainingTime }
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
                            ? qsTr("Disable shuffle") : qsTr("Enable shuffle")
                        selected: root.shuffleEnabled
                        enabled: root.hasPlayableMedia
                        onClicked: root.shuffleRequested(!root.shuffleEnabled)
                    }
                    MichiIconButton {
                        objectName: "previousButton"
                        iconName: "previous"
                        accessibleName: qsTr("Previous track")
                        enabled: root.hasPrevious
                        onClicked: root.previousRequested()
                    }

                    Button {
                        id: playPauseButton
                        objectName: "playPauseButton"
                        Layout.preferredWidth: 55
                        Layout.preferredHeight: 54
                        enabled: root.hasPlayableMedia
                        focusPolicy: Qt.StrongFocus
                        hoverEnabled: true
                        Accessible.role: Accessible.Button
                        Accessible.name: root.status === "playing" ? qsTr("Pause") : qsTr("Play")
                        onClicked: root.playPauseRequested()

                        contentItem: Item {
                            anchors.centerIn: parent
                            width: 28
                            height: 28
                            // Crossfade between play/pause (position and
                            // size unchanged — only opacity/scale animate)
                            MichiIcon {
                                anchors.fill: parent
                                name: "play"
                                iconColor: playPauseButton.enabled
                                    ? MichiPalette.auroraCyan : MichiPalette.textDisabled
                                strokeWidth: 2
                                opacity: root.status === "playing" ? 0 : 1
                                scale: root.status === "playing" ? 0.6 : 1
                                Behavior on opacity {
                                    enabled: !MichiAccessibility.reducedMotion
                                    NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                                }
                                Behavior on scale {
                                    enabled: !MichiAccessibility.reducedMotion
                                    NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                                }
                            }
                            MichiIcon {
                                anchors.fill: parent
                                name: "pause"
                                iconColor: playPauseButton.enabled
                                    ? MichiPalette.auroraCyan : MichiPalette.textDisabled
                                strokeWidth: 2
                                opacity: root.status === "playing" ? 1 : 0
                                scale: root.status === "playing" ? 1 : 0.6
                                Behavior on opacity {
                                    enabled: !MichiAccessibility.reducedMotion
                                    NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                                }
                                Behavior on scale {
                                    enabled: !MichiAccessibility.reducedMotion
                                    NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                                }
                            }
                        }
                        background: Rectangle {
                            radius: 17
                            // Tinted material: vertical gradient base with
                            // a state overlay on top (pressed/hovered)
                            gradient: Gradient {
                                orientation: Gradient.Vertical
                                GradientStop { position: 0; color: MichiPalette.smokeRaised }
                                GradientStop { position: 1; color: MichiPalette.smoke }
                            }
                            border.width: 1
                            border.color: playPauseButton.visualFocus
                                ? MichiSemanticColors.focusRing
                                : root.status === "playing"
                                    ? MichiSemanticColors.auroraCyanBorder
                                    : MichiSemanticColors.borderStrong
                            scale: playPauseButton.pressed ? 0.96
                                : playPauseButton.hovered ? 1.025 : 1

                            Rectangle {
                                anchors.fill: parent
                                radius: 17
                                color: playPauseButton.pressed
                                    ? MichiSemanticColors.surfacePressed
                                    : playPauseButton.hovered
                                        ? MichiSemanticColors.surfaceHover : "transparent"
                            }

                            // Soft radial glow aura during playback, gently
                            // breathing (2.4s cycle)
                            Rectangle {
                                anchors.centerIn: parent
                                width: parent.width + 6
                                height: parent.height + 6
                                radius: 20
                                color: "transparent"
                                border.width: 1
                                border.color: MichiSemanticColors.auroraCyanBorderSubtle
                                visible: root.status === "playing"
                                opacity: 0.6
                                SequentialAnimation on opacity {
                                    running: root.status === "playing"
                                        && !MichiAccessibility.reducedMotion
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.6; duration: 1200; easing.type: MichiMotion.outCubic }
                                    NumberAnimation { to: 0.22; duration: 1200; easing.type: MichiMotion.inOutCubic }
                                }
                            }

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
                        accessibleName: qsTr("Next track")
                        enabled: root.hasNext
                        onClicked: root.nextRequested()
                    }
                    MichiIconButton {
                        objectName: "repeatButton"
                        iconName: root.repeatMode === "ONE" ? "repeat-one" : "repeat"
                        accessibleName: qsTr("Repeat: %1")
                            .arg(root.repeatMode.toLowerCase())
                        selected: root.repeatMode !== "NONE"
                        // Repeat ALL vs NONE share the same glyph — the
                        // dimmed opacity adds a non-chromatic differentiator
                        opacity: root.repeatMode === "NONE" ? 0.45 : 1
                        Behavior on opacity {
                            enabled: !MichiAccessibility.reducedMotion
                            NumberAnimation { duration: MichiMotion.micro }
                        }
                        enabled: root.hasPlayableMedia
                        onClicked: root.repeatRequested(nextRepeatMode(root.repeatMode))
                    }
                }
            }
        }

        GridLayout {
            id: outputZone
            objectName: "outputZone"
            columns: 4
            columnSpacing: MichiSpacing.xs
            rowSpacing: MichiSpacing.sm
            Layout.preferredWidth: root.compact ? 286 : 330
            Layout.minimumWidth: 270
            Layout.maximumWidth: 350
            Layout.preferredHeight: root.height - 40
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop

            MichiIconButton {
                objectName: "muteButton"
                Layout.row: 0
                Layout.column: 0
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                iconName: root.muted || root.volume === 0 ? "mute" : "volume"
                accessibleName: root.muted ? qsTr("Unmute") : qsTr("Mute")
                onClicked: root.muteRequested(!root.muted)
            }

            RowLayout {
                objectName: "volumeControlRow"
                Layout.row: 0
                Layout.column: 1
                Layout.fillWidth: true
                Layout.minimumWidth: 130
                Layout.preferredHeight: 34
                spacing: MichiSpacing.xs

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
                    Accessible.name: qsTr("Volume")
                    Accessible.description: qsTr("%1 percent")
                        .arg(Math.round(value))
                    onMoved: root.volumeRequested(Math.round(value))

                    background: Rectangle {
                        x: volumeSlider.leftPadding
                        y: volumeSlider.topPadding
                            + volumeSlider.availableHeight / 2 - height / 2
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
                        x: volumeSlider.leftPadding + volumeSlider.visualPosition
                            * (volumeSlider.availableWidth - width)
                        y: volumeSlider.topPadding
                            + volumeSlider.availableHeight / 2 - height / 2
                        width: 14
                        height: 14
                        radius: 7
                        color: MichiPalette.textPrimary
                        border.width: 2
                        border.color: volumeSlider.visualFocus
                            || volumeSlider.hovered
                            ? MichiPalette.auroraCyan : MichiPalette.auroraPurple
                        scale: volumeSlider.pressed ? 1.08
                            : volumeSlider.hovered ? 1.04 : 1
                        Behavior on scale {
                            enabled: !MichiAccessibility.reducedMotion
                            NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                        }
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
                    Layout.preferredWidth: 34
                    text: Math.round(volumeSlider.value) + "%"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    horizontalAlignment: Text.AlignRight
                }
            }

            MichiIconButton {
                objectName: "settingsButton"
                Layout.row: 0
                Layout.column: 2
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                iconName: "equalizer"
                accessibleName: qsTr("Audio settings")
                onClicked: root.settingsRequested()
            }

            MichiIconButton {
                objectName: "outputDeviceButton"
                Layout.row: 0
                Layout.column: 3
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                iconName: "audio-output"
                accessibleName: qsTr("Output selection unavailable")
                enabled: false
                opacity: 0.62
            }

            // M11.3-UI: real interactive engine quick-selector.
            // Quick selection only — no configuration, no DAC, no details.
            // The popup stays LIVE-BOUND to the projections below: engine
            // state is never copied imperatively, so it updates while open.
            MichiIconButton {
                objectName: "audioEngineButton"
                Layout.row: 1
                Layout.column: 0
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                iconName: "audio-engine"
                accessibleName: root.audioEngineTooltip()
                checkable: true
                checked: enginePopup.opened
                onClicked: {
                    // Paint cached facts immediately. The isolated refresh
                    // updates the live-bound rows after the popup is visible.
                    enginePopup.open()
                    root.audioEngineRefreshRequested()
                }
                Accessible.name: root.audioEngineTooltip()
            }

            AudioEnginePopup {
                id: enginePopup
                y: -height - MichiSpacing.md
                x: 0
                // LIVE BINDINGS (M11.3-UI-R1): no imperative copies — the
                // popup always mirrors the current bridge projections,
                // including while it is open.
                engines: root.audioEngines
                selectedEngineId: root.selectedEngineId
                activeEngineId: root.activeEngineId
                switchingTo: root.audioEngineSwitchingTo
                fallbackFrom: root.audioEngineFallbackFrom
                hasFallback: root.audioEngineFallbackFrom !== ""
                    && root.selectedEngineId !== root.activeEngineId
                statusSummary: root.audioEngineStatusSummary
                engineSwitchReady: root.audioEngineSwitchReady
                engineSwitchBlocker: root.audioEngineSwitchBlocker
                onEngineSwitchRequested: (engineId) =>
                    root.audioEngineSwitchRequested(engineId)
            }

            Rectangle {
                id: qualityBadge
                objectName: "qualityBadge"
                Layout.row: 1
                Layout.column: 1
                Layout.fillWidth: true
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
                        width: 7
                        height: 7
                        radius: 4
                        color: root.hasTrack
                            ? MichiPalette.auroraGreen : MichiPalette.textMuted
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

            MichiIconButton {
                objectName: "queueButton"
                Layout.row: 1
                Layout.column: 2
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                iconName: "queue"
                accessibleName: "Open queue"
                onClicked: root.queueRequested()
            }

            Item {
                Layout.row: 1
                Layout.column: 3
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
            }

            Item {
                Layout.row: 2
                Layout.column: 0
                Layout.columnSpan: 4
                Layout.fillHeight: true
            }
        }
    }

    function audioEngineTooltip() {
        // Friendly names only — never canonical IDs, never diagnostics.
        if (root.audioEngineActiveName === "")
            return qsTr("Audio engine")
        if (root.audioEngineFallbackFrom !== ""
                && root.selectedEngineId !== root.activeEngineId)
            return qsTr("%1 in use · %2 preferred")
                .arg(root.audioEngineActiveName, root.audioEngineSelectedName)
        return qsTr("Audio engine: %1").arg(root.audioEngineActiveName)
    }

    function formatTime(seconds) {
        // Delegates to the shared formatter (position values are seconds;
        // MichiFormat expects ms — the floor semantics match exactly).
        return MichiFormat.formatDuration(seconds * 1000)
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
