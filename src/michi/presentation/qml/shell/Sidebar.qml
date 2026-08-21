import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    signal navigationRequested(string routeId)
    signal createPlaylistRequested()
    property string currentRoute: ""
    property bool compact: false
    contentPadding: MichiSpacing.sm
    elevation: "elevated"
    shadowed: true
    textured: true
    accented: true
    accentColor: MichiPalette.auroraPurple

    readonly property bool _playlistsActive: root.currentRoute === "playlists"
    // PLAYLIST-HIERARCHY-03: all canonical playlist navigation resolves
    // through AppRoute.PLAYLISTS — selected row = PLAYLISTS + playlistId.

    readonly property var _routes: [
        { id: "now_playing", label: "Now Playing", icon: "play" },
        { id: "library", label: "Library", icon: "library" }
    ]

    readonly property var _bottom_routes: [
        { id: "settings", label: "Settings", icon: "settings" }
    ]

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        opacity: 0.62
        z: 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: MichiSemanticColors.auroraPurpleSurface
            }
            GradientStop { position: 0.46; color: "transparent" }
            GradientStop {
                position: 1
                color: MichiSemanticColors.auroraCyanSurface
            }
        }
    }

    MichiMaterialTexture {
        anchors.fill: parent
        textureOpacity: 0.14
        z: 0
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

            contentItem: RowLayout {
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.leftMargin: MichiSpacing.md
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 10
                    color: routeItem._active
                        ? MichiSemanticColors.surfaceSelected
                        : routeItem.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    border.width: routeItem._active ? 1 : 0
                    border.color: MichiSemanticColors.auroraCyanBorderSubtle
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
                    visible: !root.compact
                    text: modelData.label
                    role: "secondary"
                    font.weight: routeItem._active ? Font.DemiBold : Font.Normal
                    color: routeItem._active || routeItem.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
                }
                Item { Layout.fillWidth: true }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: routeItem.pressed ? MichiSemanticColors.surfacePressed
                    : routeItem._active ? MichiSemanticColors.surfaceSelected
                    : routeItem.hovered || routeItem.visualFocus ? MichiSemanticColors.surfaceHover : "transparent"
                border.width: routeItem._active ? 1 : 0
                border.color: MichiSemanticColors.auroraBorderSubtle
                Rectangle {
                    visible: routeItem._active
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 3
                    radius: 2
                    gradient: Gradient {
                        GradientStop { position: 0; color: MichiPalette.auroraBlue }
                        GradientStop { position: 0.5; color: MichiPalette.auroraCyan }
                        GradientStop { position: 1; color: MichiPalette.auroraPurple }
                    }
                }
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: routeItem.visualFocus }
            }
            onClicked: root.navigationRequested(modelData.id)
        }
    }

    // Compact playlist row: rectangular, quiet content (glass = controls),
    // text ellipsis, focus-visible, selected state by PLAYLISTS + id.
    Component {
        id: playlistRowDelegate
        ItemDelegate {
            id: playlistItem
            Layout.fillWidth: true
            height: MichiMetrics.controlLarge
            readonly property bool _active: root._playlistsActive
                && (playlists.selectedPlaylistId === modelData.playlistId
                    || (modelData.playlistId === "" && playlists.selectedPlaylistId === ""))
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Accessible.role: Accessible.Button
            Accessible.name: modelData.name

            contentItem: RowLayout {
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.leftMargin: MichiSpacing.md
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    radius: 8
                    color: playlistItem._active
                        ? MichiSemanticColors.surfaceSelected
                        : playlistItem.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    MichiIcon {
                        anchors.centerIn: parent
                        name: "playlist"
                        width: 15
                        height: 15
                        strokeWidth: playlistItem._active ? 2.0 : 1.8
                        iconColor: playlistItem._active ? MichiPalette.auroraCyan
                            : playlistItem.hovered ? MichiPalette.textPrimary
                            : MichiPalette.textSecondary
                    }
                }
                MichiText {
                    visible: !root.compact
                    text: modelData.name
                    role: "secondary"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    font.weight: playlistItem._active ? Font.DemiBold : Font.Normal
                    color: playlistItem._active || playlistItem.hovered
                        ? MichiPalette.textPrimary : MichiPalette.textSecondary
                }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: playlistItem.pressed ? MichiSemanticColors.surfacePressed
                    : playlistItem._active ? MichiSemanticColors.surfaceSelected
                    : playlistItem.hovered || playlistItem.visualFocus ? MichiSemanticColors.surfaceHover : "transparent"
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: playlistItem.visualFocus }
            }
            onClicked: {
                if (modelData.playlistId === "")
                    playlists.open_all_playlists()
                else
                    playlists.open_playlist(modelData.playlistId)
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
                    color: MichiSemanticColors.auroraPurpleSurface
                    border.width: 1
                    border.color: MichiSemanticColors.auroraPurpleBorder
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 4
                        radius: 11
                        color: MichiSemanticColors.auroraCyanSurface
                    }
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
                    visible: !root.compact
                    spacing: 0
                    MichiText {
                        text: "Michi"
                        role: "title"
                        color: MichiPalette.textPrimary
                        font.weight: Font.DemiBold
                    }
                    MichiText {
                        text: "LOCAL HI-FI"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    visible: !root.compact
                    Layout.preferredWidth: 7
                    Layout.preferredHeight: 7
                    radius: 4
                    color: library.fileCount > 0
                        ? MichiPalette.auroraGreen : MichiPalette.textMuted
                }
            }
        }

        MichiText {
            visible: !root.compact
            Layout.leftMargin: MichiSpacing.md
            Layout.topMargin: MichiSpacing.sm
            Layout.bottomMargin: MichiSpacing.xs
            text: "NAVIGATION"
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }

        Repeater {
            model: root._routes
            delegate: routeDelegate
        }

        // PLAYLIST-HIERARCHY-01/02: Playlists is a first-class Shell
        // section — independent from NAVIGATION and SETTINGS.
        MichiText {
            visible: !root.compact
            Layout.leftMargin: MichiSpacing.md
            Layout.topMargin: MichiSpacing.md
            Layout.bottomMargin: MichiSpacing.xs
            text: "PLAYLISTS"
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }

        // All Playlists: PLAYLISTS + None
        ItemDelegate {
            Layout.fillWidth: true
            height: MichiMetrics.controlLarge
            readonly property bool _active: root._playlistsActive
                && playlists.selectedPlaylistId === ""
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Open All Playlists")
            contentItem: RowLayout {
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.leftMargin: MichiSpacing.md
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    radius: 8
                    color: parent.parent._active
                        ? MichiSemanticColors.surfaceSelected
                        : parent.parent.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    MichiIcon {
                        anchors.centerIn: parent
                        name: "playlist"
                        width: 15
                        height: 15
                        strokeWidth: parent.parent._active ? 2.0 : 1.8
                        iconColor: parent.parent._active ? MichiPalette.auroraCyan
                            : parent.parent.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
                    }
                }
                MichiText {
                    visible: !root.compact
                    text: qsTr("All Playlists")
                    role: "secondary"
                    font.weight: parent.parent._active ? Font.DemiBold : Font.Normal
                    color: parent.parent._active || parent.parent.hovered
                        ? MichiPalette.textPrimary : MichiPalette.textSecondary
                }
                Item { Layout.fillWidth: true }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: parent.pressed ? MichiSemanticColors.surfacePressed
                    : parent._active ? MichiSemanticColors.surfaceSelected
                    : parent.hovered || parent.visualFocus ? MichiSemanticColors.surfaceHover : "transparent"
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: parent.visualFocus }
            }
            onClicked: playlists.open_all_playlists()
        }

        // Pinned quick access — bounded to 5 visible rows (scalability rule:
        // never render every playlist permanently; the rest live in
        // All Playlists).
        MichiText {
            visible: !root.compact && playlists.pinnedPlaylists.length > 0
            Layout.leftMargin: MichiSpacing.md
            Layout.topMargin: MichiSpacing.sm
            Layout.bottomMargin: MichiSpacing.xs
            text: "PINNED"
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        Repeater {
            model: playlists.pinnedPlaylists.slice(0, 5)
            delegate: playlistRowDelegate
        }

        MichiText {
            visible: !root.compact && playlists.recentPlaylists.length > 0
            Layout.leftMargin: MichiSpacing.md
            Layout.topMargin: MichiSpacing.sm
            Layout.bottomMargin: MichiSpacing.xs
            text: "RECENT"
            role: "technical"
            technical: true
            color: MichiPalette.textMuted
        }
        Repeater {
            model: playlists.recentPlaylists.slice(0, 5)
            delegate: playlistRowDelegate
        }

        // + New Playlist affordance
        ItemDelegate {
            Layout.fillWidth: true
            height: MichiMetrics.controlLarge
            focusPolicy: Qt.StrongFocus
            hoverEnabled: true
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Create playlist")
            contentItem: RowLayout {
                spacing: MichiSpacing.md
                Rectangle {
                    Layout.leftMargin: MichiSpacing.md
                    Layout.preferredWidth: 28
                    Layout.preferredHeight: 28
                    radius: 8
                    color: parent.parent.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    border.width: 1
                    border.color: MichiSemanticColors.borderSubtle
                    MichiIcon {
                        anchors.centerIn: parent
                        name: "plus"
                        width: 15
                        height: 15
                        iconColor: MichiPalette.auroraGreen
                    }
                }
                MichiText {
                    visible: !root.compact
                    text: qsTr("New Playlist")
                    role: "secondary"
                    color: parent.parent.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
                }
                Item { Layout.fillWidth: true }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: parent.hovered || parent.visualFocus ? MichiSemanticColors.surfaceHover : "transparent"
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: parent.visualFocus }
            }
            onClicked: root.createPlaylistRequested()
        }

        Item { Layout.fillHeight: true }

        MichiGlassSurface {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            Layout.bottomMargin: MichiSpacing.xs
            elevation: "subtle"
            contentPadding: MichiSpacing.sm
            textured: true
            accented: library.fileCount > 0
            accentColor: MichiPalette.auroraCyan

            ColumnLayout {
                anchors.fill: parent
                spacing: MichiSpacing.xs
                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiSpacing.xs
                    Rectangle {
                        Layout.preferredWidth: 7
                        Layout.preferredHeight: 7
                        radius: 4
                        color: library.fileCount > 0
                            ? MichiPalette.auroraGreen : MichiPalette.textMuted
                    }
                    MichiText {
                        text: "LOCAL"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    Item { Layout.fillWidth: true }
                }
                MichiText {
                    text: library.fileCount > 0
                        ? library.fileCount + " tracks" : "Ready to scan"
                    role: "secondary"
                    font.weight: Font.DemiBold
                }
                MichiText {
                    text: library.fileCount > 0
                        ? library.albumCount + " albums · "
                            + library.artistCount + " artists"
                        : "Your collection stays on this device"
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
        Item { Layout.preferredHeight: MichiSpacing.xs }
        Repeater {
            model: root._bottom_routes
            delegate: routeDelegate
        }
    }
}
