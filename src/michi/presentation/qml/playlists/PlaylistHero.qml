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

    property string playlistName: ""
    property int trackCount: 0
    property int durationMs: 0
    property string description: ""
    property string customCoverPath: ""
    property var mosaicArtworkPaths: []
    property bool pinned: false
    property bool hasTracks: root.trackCount > 0

    signal playRequested()
    signal shuffleRequested()
    signal moreRequested()
    signal changeCoverRequested()
    signal togglePinRequested()

    // Editorial header height (~30-40% of the first screen); the page
    // overrides this to track the window height.
    implicitHeight: 260

    // Atmospheric depth only — never a saturated glow
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiPalette.playlistHeroTop }
            GradientStop { position: 0.55; color: MichiPalette.playlistHeroMid }
            GradientStop { position: 1; color: MichiPalette.playlistHeroBottom }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiSpacing.xl
        anchors.rightMargin: MichiSpacing.xl
        anchors.topMargin: MichiSpacing.lg
        anchors.bottomMargin: MichiSpacing.lg
        spacing: MichiSpacing.xl

        // Dominant square cover, 136px, soft rounded corners, faint shadow
        Item {
            Layout.preferredWidth: 136
            Layout.preferredHeight: 136

            // Very faint diffuse shadow — separation, not glow
            Rectangle {
                anchors.fill: parent
                anchors.margins: -6
                radius: 16
                color: MichiSemanticColors.glassShadowFar
                opacity: 0.55
                z: -1
            }

            PlaylistArtwork {
                anchors.fill: parent
                customCoverPath: root.customCoverPath
                mosaicArtworkPaths: root.mosaicArtworkPaths
                fallbackText: root.playlistName
                radius: 10
            }

            // Quiet "change cover" affordance (hover / keyboard focus)
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.changeCoverRequested()

                Rectangle {
                    anchors.fill: parent
                    radius: 10
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
                    Accessible.name: qsTr("Change playlist cover")
                    Keys.onReturnPressed: root.changeCoverRequested()
                    Keys.onEnterPressed: root.changeCoverRequested()
                    Keys.onSpacePressed: root.changeCoverRequested()
                }
                MichiFocusRing { visualFocus: coverFocus.activeFocus && MichiAccessibility.keyboardMode }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: MichiSpacing.sm

            // Eyebrow: quiet uppercase type label
            MichiText {
                text: qsTr("PLAYLIST")
                role: "technical"
                technical: true
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

            // Compact secondary metadata
            MichiText {
                Layout.fillWidth: true
                text: {
                    var parts = []
                    if (root.trackCount > 0)
                        parts.push(root.trackCount + (root.trackCount === 1 ? qsTr(" song") : qsTr(" songs")))
                    if (root.durationMs > 0)
                        parts.push(MichiFormat.formatHoursMinutes(root.durationMs))
                    if (parts.length === 0)
                        parts.push(qsTr("Empty playlist"))
                    return parts.join(" · ")
                }
                role: "secondary"
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
                MichiIconButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    iconName: "shuffle"
                    accessibleName: qsTr("Shuffle playlist")
                    enabled: root.hasTracks
                    onClicked: root.shuffleRequested()
                }
                MichiIconButton {
                    implicitWidth: 28
                    implicitHeight: 28
                    iconName: "pin"
                    selected: root.pinned
                    accessibleName: root.pinned
                        ? qsTr("Unpin playlist") : qsTr("Pin playlist")
                    onClicked: root.togglePinRequested()
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
