import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistHero — editorial header of the playlist page. One continuous
// surface: deep low-saturation blue atmosphere behind a dominant square
// cover and compact metadata. Deliberately NOT a glass card — the hero
// flows into the track table below.
Item {
    id: root
    objectName: "playlistHero"

    property string playlistName: ""
    property int trackCount: 0
    property int durationMs: 0
    property string description: ""
    property string customCoverPath: ""
    property var mosaicArtworkPaths: []
    property string heroMode: "auto"
    property color heroSolidColor: MichiPalette.playlistHeroTop
    property var heroGradientColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
    property real heroGradientAngle: 135
    property string heroImagePath: ""
    property var autoHeroColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid, MichiPalette.playlistHeroBottom]
    property bool pinned: false
    property bool hasTracks: root.trackCount > 0
    readonly property real coverSize: width >= 960 ? 176 : width >= 720 ? 164 : 148

    signal playRequested()
    signal shuffleRequested()
    signal moreRequested()
    signal customizeAppearanceRequested()
    signal togglePinRequested()
    signal addTracksRequested()

    // Editorial header height (~30-40% of the first screen). Self-sized
    // from the hosting view (the ListView header's parent) — the page must
    // NOT pass a height here: inside this component scope `root` is this
    // hero, so any page-root reference in a property binding would collapse
    // the header to zero height.
    implicitHeight: Math.max(240, Math.min(300, (parent ? parent.height : 600) * 0.36))

    // Quiet entrance fade when the route opens (reduced-motion gated)
    opacity: 0
    Behavior on opacity {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation { duration: MichiMotion.panel; easing.type: MichiMotion.outCubic }
    }
    Component.onCompleted: opacity = 1

    PlaylistHeroBackground {
        anchors.fill: parent
        heroMode: root.heroMode
        solidColor: root.heroSolidColor
        gradientColors: root.heroGradientColors
        gradientAngle: root.heroGradientAngle
        heroImagePath: root.heroImagePath
        coverPath: root.customCoverPath
        mosaicArtworkPaths: root.mosaicArtworkPaths
        autoColors: root.autoHeroColors
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.xl
        anchors.rightMargin: MichiSpacing.xl
        anchors.topMargin: MichiSpacing.lg
        anchors.bottomMargin: MichiSpacing.lg
        spacing: MichiSpacing.xl

        // Dominant responsive cover: 160–180px when the viewport permits.
        Item {
            id: coverStage
            Layout.preferredWidth: root.coverSize
            Layout.preferredHeight: root.coverSize
            scale: 0.985
            Behavior on scale {
                enabled: !MichiAccessibility.reducedMotion
                NumberAnimation { duration: MichiMotion.artwork; easing.type: MichiMotion.outCubic }
            }
            Component.onCompleted: scale = 1

            // Very faint diffuse shadow — separation, not glow
            Rectangle {
                anchors.fill: parent
                anchors.margins: -6
                radius: MichiRadius.floating
                color: MichiSemanticColors.glassShadowFar
                opacity: 0.55
                z: -1
            }

            PlaylistArtwork {
                anchors.fill: parent
                customCoverPath: root.customCoverPath
                mosaicArtworkPaths: root.mosaicArtworkPaths
                fallbackText: root.playlistName
                radius: MichiRadius.lg
            }

            // Quiet "change cover" affordance (hover / keyboard focus)
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.customizeAppearanceRequested()

                Rectangle {
                    anchors.fill: parent
                    radius: MichiRadius.lg
                    color: MichiPalette.obsidianDeep
                    opacity: parent.containsMouse || coverFocus.activeFocus ? 0.55 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.micro; easing.type: MichiMotion.outCubic }
                    }
                    MichiIcon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        name: "sliders"
                        iconColor: MichiPalette.textPrimary
                        opacity: 0.85
                    }
                }
                Item {
                    id: coverFocus
                    anchors.fill: parent
                    focusPolicy: Qt.StrongFocus
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button
                    Accessible.name: qsTr("Customize playlist appearance")
                    Keys.onReturnPressed: root.customizeAppearanceRequested()
                    Keys.onEnterPressed: root.customizeAppearanceRequested()
                    Keys.onSpacePressed: root.customizeAppearanceRequested()
                }
                MichiFocusRing { visualFocus: coverFocus.activeFocus && MichiAccessibility.keyboardMode }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: MichiSpacing.sm

            // Eyebrow: quiet uppercase type label (10-11px per spec)
            MichiText {
                text: qsTr("PLAYLIST")
                role: "caption"
                color: MichiPalette.textSecondary
                opacity: 0.62
                font.weight: Font.DemiBold
                font.letterSpacing: 1.4
            }

            // Dominant typographic element
            MichiText {
                Layout.fillWidth: true
                text: root.playlistName
                role: "display"
                font.weight: Font.DemiBold
                color: MichiPalette.textPrimary
                elide: Text.ElideRight
            }

            // Compact secondary metadata (11-12px per spec)
            MichiText {
                Layout.fillWidth: true
                text: MichiFormat.formatPlaylistSummary(root.trackCount, root.durationMs)
                role: "technical"
                color: MichiPalette.textSecondary
                opacity: 0.65
            }

            // Optional description, hard-capped at two lines
            MichiText {
                Layout.fillWidth: true
                visible: root.description.length > 0
                text: root.description
                role: "secondary"
                color: MichiPalette.textSecondary
                opacity: 0.6
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            Item { Layout.preferredHeight: MichiSpacing.xs }

            // Primary + secondary actions — compact, discrete
            RowLayout {
                spacing: MichiSpacing.md

                MichiButton {
                    text: qsTr("Play")
                    iconName: "play"
                    variant: "primary"
                    implicitHeight: MichiMetrics.controlMedium
                    enabled: root.hasTracks
                    accessibleName: qsTr("Play playlist now")
                    onClicked: root.playRequested()
                }
                MichiButton {
                    text: parent.width < 820 ? "" : qsTr("Customize")
                    iconName: "sliders"
                    iconOnly: parent.width < 820
                    variant: "ghost"
                    implicitHeight: MichiMetrics.controlSmall
                    accessibleName: qsTr("Customize playlist appearance")
                    onClicked: root.customizeAppearanceRequested()
                }
                MichiIconButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    iconName: "shuffle"
                    accessibleName: qsTr("Shuffle playlist")
                    enabled: root.hasTracks
                    onClicked: root.shuffleRequested()
                }
                MichiButton {
                    // icon-only on narrow windows so the action row never
                    // crowds the title block
                    text: parent.width < 700 ? "" : qsTr("Add tracks")
                    iconName: "plus"
                    variant: "ghost"
                    implicitHeight: 30
                    implicitWidth: parent.width < 700 ? 30 : undefined
                    accessibleName: qsTr("Add tracks from library")
                    onClicked: root.addTracksRequested()
                }
                MichiIconButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    iconName: "more"
                    accessibleName: qsTr("More playlist options")
                    onClicked: root.moreRequested()
                }
            }
        }
    }
}
