import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    signal navigationRequested(string routeId)
    property string currentRoute: ""
    property bool compact: false
    contentPadding: MichiSpacing.sm
    elevation: "elevated"
    tileSeed: 1
    shadowed: true
    textured: true
    // True smoke glass: always-on backdrop blur + translucent smoked
    // material, so the content scrolling behind reads through softly.
    forceBlur: true
    materialOpacityOverride: 0.68
    // Finer grain than cards (navigation surface, not a tile) and a
    // discreet brand glint — ultra-premium restraint.
    textureOpacityOverride: 0.18
    glintScale: 0.4
    accented: true
    // Single accent per surface: cyan (the functional active state) —
    // the previous auroraPurple glass accent competed with the cyan
    // active item and the blue/purple ambient gradient (chromatic noise).
    accentColor: MichiPalette.auroraCyan

    readonly property var _routes: [
        { id: "now_playing", label: qsTr("Now Playing"), icon: "play" },
        { id: "library", label: qsTr("Library"), icon: "library" },
        { id: "playlists", label: qsTr("Playlists"), icon: "playlist" }
    ]

    readonly property var _bottom_routes: [
        { id: "settings", label: qsTr("Settings"), icon: "settings" }
    ]

    function libraryReady() {
        return typeof library !== "undefined" && library && library.fileCount > 0
    }

    // Deep-blue atmosphere, extended for vertical depth — one hue family
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        opacity: 0.16
        z: 0
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: MichiSemanticColors.contentAmbientBlue }
            GradientStop { position: 0.6; color: "transparent" }
        }
    }

    Component {
        id: routeDelegate
        ItemDelegate {
            id: routeItem
            Layout.fillWidth: true
            height: MichiMetrics.controlLarge
            readonly property bool _active: root.currentRoute === modelData.id
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Accessible.role: Accessible.Button
            Accessible.name: modelData.label
            Accessible.checked: routeItem._active

            contentItem: RowLayout {
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.leftMargin: MichiSpacing.md
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 8
                    color: routeItem._active
                        ? MichiSemanticColors.surfaceSelected
                        : routeItem.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    MichiIcon {
                        anchors.centerIn: parent
                        name: modelData.icon
                        width: 18
                        height: 18
                        strokeWidth: routeItem._active ? 2.0 : 1.8
                        iconColor: routeItem._active ? MichiPalette.auroraCyan
                            : routeItem.hovered ? MichiPalette.textPrimary
                            : MichiPalette.textSecondary
                    }
                }
                MichiText {
                    text: modelData.label
                    role: "secondary"
                    // Fade the label when collapsing to compact (width and
                    // opacity animate together — no layout pop)
                    opacity: root.compact ? 0 : 1
                    Layout.preferredWidth: root.compact ? 0 : implicitWidth
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                    }
                    Behavior on Layout.preferredWidth {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                    }
                    font.weight: routeItem._active ? Font.DemiBold : Font.Normal
                    color: routeItem._active || routeItem.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
                }
                // Playlist count badge (quiet, informational)
                MichiText {
                    visible: modelData.id === "playlists"
                        && typeof playlists !== "undefined" && playlists
                        && playlists.playlists && !root.compact
                    text: playlists.playlists.length
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    Layout.alignment: Qt.AlignVCenter
                    Layout.rightMargin: MichiSpacing.md
                    opacity: 0.85
                }
                Item { Layout.fillWidth: true }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: routeItem.pressed ? MichiSemanticColors.surfacePressed
                    : routeItem._active ? MichiSemanticColors.surfaceSelected
                    : routeItem.hovered || routeItem.visualFocus ? MichiSemanticColors.surfaceHover : "transparent"
                border.width: routeItem._active ? 1 : 0
                border.color: MichiSemanticColors.auroraCyanBorderSubtle

                Rectangle {
                    visible: routeItem._active
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.topMargin: 8
                    anchors.bottomMargin: 8
                    anchors.leftMargin: 1
                    width: 3
                    radius: 1.5
                    color: MichiPalette.auroraCyan
                }
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: routeItem.visualFocus }
            }
            onClicked: root.navigationRequested(modelData.id)

            // Compact mode hides the labels — the tooltip keeps the
            // route name discoverable on hover
            MichiTooltip {
                visible: root.compact && routeItem.hovered
                text: modelData.label
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xs
        z: 1

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: root.compact ? 8 : MichiSpacing.md
                anchors.rightMargin: root.compact ? 8 : MichiSpacing.md
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    radius: 14
                    // Single-accent brand tile: cyan on deep obsidian
                    color: MichiPalette.obsidianRaised
                    border.width: 1
                    border.color: MichiSemanticColors.auroraCyanBorderSubtle
                    MichiIcon {
                        anchors.centerIn: parent
                        width: 23
                        height: 23
                        name: "cat"
                        iconColor: MichiPalette.auroraCyan
                        strokeWidth: 1.9
                    }
                }
                ColumnLayout {
                    spacing: 0
                    opacity: root.compact ? 0 : 1
                    Layout.preferredWidth: root.compact ? 0 : implicitWidth
                    Behavior on opacity {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                    }
                    Behavior on Layout.preferredWidth {
                        enabled: !MichiAccessibility.reducedMotion
                        NumberAnimation { duration: MichiMotion.standard; easing.type: MichiMotion.outCubic }
                    }
                    MichiText {
                        text: "Michi"
                        role: "title"
                        color: MichiPalette.textPrimary
                        font.weight: Font.DemiBold
                    }
                    // State chip: shape + color + text (never color-only)
                    MichiStatusChip {
                        text: root.libraryReady() ? qsTr("READY") : qsTr("EMPTY")
                        tone: root.libraryReady() ? "success" : "neutral"
                        dotVisible: true
                        implicitHeight: 18
                    }
                }
            }
        }

        Item { Layout.preferredHeight: MichiSpacing.xs }

        Repeater {
            model: root._routes
            delegate: routeDelegate
        }

        Item { Layout.fillHeight: true }

        // Subtle compact Local indicator
        Rectangle {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.preferredHeight: 28
            Layout.leftMargin: MichiSpacing.md
            Layout.rightMargin: MichiSpacing.md
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                spacing: MichiSpacing.sm
                Rectangle {
                    Layout.preferredWidth: 6
                    Layout.preferredHeight: 6
                    radius: 3
                    color: (typeof library !== "undefined" && library && library.fileCount > 0)
                        ? MichiPalette.auroraGreen : MichiPalette.textMuted
                }
                MichiText {
                    text: (typeof library !== "undefined" && library && library.fileCount > 0)
                        ? qsTr("Local · %n track(s)", "", library.fileCount)
                        : qsTr("Local · Ready")
                    role: "caption"
                    color: MichiPalette.textSecondary
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        Item { Layout.preferredHeight: MichiSpacing.xs }

        Rectangle {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.leftMargin: MichiSpacing.md
            Layout.rightMargin: MichiSpacing.md
            color: MichiSemanticColors.borderSubtle
            opacity: 0.6
        }

        Item { Layout.preferredHeight: MichiSpacing.xs }

        Repeater {
            model: root._bottom_routes
            delegate: routeDelegate
        }
    }
}
