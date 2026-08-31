import QtQuick
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistHero — a real, self-contained editorial surface. The parent owns
// its explicit width/height; this component never relies on child overflow.
Item {
    id: root
    objectName: "playlistHero"

    property string playlistName: ""
    property int trackCount: 0
    property int durationMs: 0
    // PL-FINAL-05/16: descripción real del playlist + conteo honesto de
    // tracks que la biblioteca no puede resolver.
    property string description: ""
    property int unavailableCount: 0

    property string customCoverPath: ""
    property var mosaicArtworkPaths: []
    property string heroMode: "auto"
    property color heroSolidColor: MichiPalette.playlistHeroTop
    property var heroGradientColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid]
    property real heroGradientAngle: 135
    property string heroImagePath: ""
    property var autoHeroColors: [MichiPalette.playlistHeroTop, MichiPalette.playlistHeroMid, MichiPalette.playlistHeroBottom]
    // PL-FINAL-09: focal del hero image (0..1) — se propaga al background.
    property real heroFocalX: 0.5
    property real heroFocalY: 0.5
    property bool hasTracks: root.trackCount > 0

    readonly property bool compact: width < 720
    readonly property real coverSize: width >= 1120 ? 180
        : width >= 820 ? 172 : width >= 620 ? 156 : 144

    signal playRequested()
    signal shuffleRequested()
    signal moreRequested()
    signal customizeAppearanceRequested()
    signal addTracksRequested()

    implicitHeight: Math.max(248, Math.min(300,
        (parent ? parent.height : 760) * 0.36))
    clip: true

    // ContentHost owns the route translation; the hero only fades so the
    // two layers never accumulate into a conspicuous double movement.
    opacity: 0
    Behavior on opacity {
        enabled: !MichiAccessibility.reducedMotion
        NumberAnimation {
            duration: MichiMotion.panel
            easing.type: MichiMotion.outCubic
        }
    }
    Component.onCompleted: opacity = 1

    PlaylistHeroBackground {
        id: heroBackground
        objectName: "playlistHeroBackground"
        anchors.fill: parent
        heroMode: root.heroMode
        solidColor: root.heroSolidColor
        gradientColors: root.heroGradientColors
        gradientAngle: root.heroGradientAngle
        heroImagePath: root.heroImagePath
        coverPath: root.customCoverPath
        mosaicArtworkPaths: root.mosaicArtworkPaths
        autoColors: root.autoHeroColors
        focalX: root.heroFocalX
        focalY: root.heroFocalY
    }

    RowLayout {
        id: heroLayout
        anchors.fill: parent
        anchors.leftMargin: root.compact ? MichiSpacing.lg : MichiSpacing.xl
        anchors.rightMargin: root.compact ? MichiSpacing.lg : MichiSpacing.xl
        anchors.topMargin: MichiSpacing.lg
        anchors.bottomMargin: MichiSpacing.lg
        spacing: root.compact ? MichiSpacing.lg : MichiSpacing.xl

        Item {
            id: coverStage
            objectName: "playlistHeroCoverStage"
            Layout.preferredWidth: root.coverSize
            Layout.preferredHeight: root.coverSize
            Layout.alignment: Qt.AlignVCenter

            Rectangle {
                anchors.fill: parent
                anchors.margins: -MichiSpacing.xs
                radius: MichiRadius.floating
                color: MichiSemanticColors.glassShadow
                opacity: 0.46
                transform: Translate { y: MichiSpacing.xs }
                z: -1
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: -1
                radius: MichiRadius.lg
                color: MichiSemanticColors.glassShadowNear
                opacity: 0.34
                transform: Translate { y: 2 }
                z: -1
            }

            PlaylistArtwork {
                id: heroCover
                objectName: "playlistHeroCover"
                anchors.fill: parent
                customCoverPath: root.customCoverPath
                mosaicArtworkPaths: root.mosaicArtworkPaths
                fallbackText: root.playlistName
                radius: MichiRadius.lg
            }

            MouseArea {
                id: coverMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.customizeAppearanceRequested()

                Rectangle {
                    anchors.fill: parent
                    radius: MichiRadius.lg
                    color: MichiSemanticColors.scrim
                    opacity: coverMouse.containsMouse || coverFocus.activeFocus ? 0.54 : 0
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation {
                            duration: MichiMotion.micro
                            easing.type: MichiMotion.outCubic
                        }
                    }

                    Column {
                        anchors.centerIn: parent
                        spacing: MichiSpacing.xs
                        opacity: parent.opacity > 0 ? 1 : 0
                        MichiIcon {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: MichiMetrics.iconLarge
                            height: width
                            name: "sliders"
                            iconColor: MichiPalette.textPrimary
                        }
                        MichiText {
                            visible: root.coverSize >= 156
                            text: qsTr("Customize")
                            role: "micro"
                            color: MichiPalette.textPrimary
                        }
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
                MichiFocusRing {
                    visualFocus: coverFocus.activeFocus
                        && MichiAccessibility.keyboardMode
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: root.width >= 1200 ? 760 : 100000
            Layout.alignment: Qt.AlignVCenter
            spacing: MichiSpacing.sm

            MichiText {
                text: qsTr("PLAYLIST")
                role: "micro"
                color: MichiPalette.textSecondary
                opacity: 0.78
                font.weight: Font.DemiBold
                font.letterSpacing: 1.35
            }

            MichiText {
                Layout.fillWidth: true
                text: root.playlistName
                role: "display"
                font.weight: Font.DemiBold
                color: MichiPalette.textPrimary
                elide: Text.ElideRight
            }

            MichiText {
                Layout.fillWidth: true
                text: MichiFormat.formatPlaylistSummary(
                    root.trackCount, root.durationMs)
                    + (root.unavailableCount > 0
                        ? qsTr(" · %n unavailable", "", root.unavailableCount)
                        : "")
                role: "technical"
                color: MichiPalette.textSecondary
                opacity: 0.78
            }

            MichiText {
                Layout.fillWidth: true
                Layout.maximumWidth: 560
                visible: root.description.length > 0
                text: root.description
                role: "secondary"
                color: MichiPalette.textPrimary
                opacity: 0.82
                elide: Text.ElideRight
                maximumLineCount: 2
                wrapMode: Text.WordWrap
            }

            Item { Layout.preferredHeight: MichiSpacing.xs }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiSpacing.sm

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
                    text: root.width >= 820 ? qsTr("Shuffle") : ""
                    iconName: "shuffle"
                    iconOnly: root.width < 820
                    variant: "secondary"
                    implicitHeight: MichiMetrics.controlMedium
                    enabled: root.hasTracks
                    accessibleName: qsTr("Shuffle playlist")
                    onClicked: root.shuffleRequested()
                }

                MichiButton {
                    text: root.width >= 920 ? qsTr("Add tracks") : ""
                    iconName: "plus"
                    iconOnly: root.width < 920
                    variant: "ghost"
                    implicitHeight: MichiMetrics.controlMedium
                    accessibleName: qsTr("Add tracks from library")
                    onClicked: root.addTracksRequested()
                }

                MichiButton {
                    text: root.width >= 760
                        ? qsTr("Customize appearance") : ""
                    iconName: "sliders"
                    iconOnly: root.width < 760
                    variant: "ghost"
                    implicitHeight: MichiMetrics.controlMedium
                    accessibleName: qsTr("Customize playlist appearance")
                    onClicked: root.customizeAppearanceRequested()
                }

                MichiIconButton {
                    implicitWidth: MichiMetrics.controlMedium
                    implicitHeight: MichiMetrics.controlMedium
                    iconName: "more"
                    accessibleName: qsTr("More playlist options")
                    onClicked: root.moreRequested()
                }

                Item { Layout.fillWidth: true }
            }
        }

        Item {
            visible: root.width >= 1200
            Layout.fillWidth: true
        }
    }
}
