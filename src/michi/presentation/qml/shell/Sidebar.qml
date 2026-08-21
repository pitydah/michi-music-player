import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    signal navigationRequested(string routeId)
    property string currentRoute: ""
    property bool compact: false
    contentPadding: MichiSpacing.sm
    elevation: "standard"
    shadowed: true
    textured: true
    accented: true
    accentColor: MichiPalette.auroraPurple

    readonly property var _routes: [
        { id: "now_playing", label: "Now Playing", icon: "play" },
        { id: "library", label: "Library", icon: "library" }
    ]

    readonly property var _bottom_routes: [
        { id: "settings", label: "Settings", icon: "settings" }
    ]

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
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                    radius: 10
                    color: routeItem._active
                        ? MichiSemanticColors.surfaceSelected
                        : routeItem.hovered ? MichiSemanticColors.controlSurface : "transparent"
                    border.width: routeItem._active ? 1 : 0
                    border.color: MichiSemanticColors.auroraCyanBorderSubtle
                    MichiIcon {
                        anchors.centerIn: parent
                        name: modelData.icon
                        width: MichiMetrics.iconSmall
                        height: MichiMetrics.iconSmall
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

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.xs

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 68
            Rectangle {
                anchors.fill: parent
                radius: MichiRadius.lg
                color: MichiSemanticColors.controlSurface
                border.width: 1
                border.color: MichiSemanticColors.borderSubtle
            }
            RowLayout {
                anchors.centerIn: parent
                spacing: MichiSpacing.sm
                Rectangle {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 12
                    color: MichiSemanticColors.auroraPurpleSurface
                    border.width: 1
                    border.color: MichiSemanticColors.auroraPurpleBorder
                    MichiIcon {
                        anchors.centerIn: parent
                        width: 21
                        height: 21
                        name: "cat"
                        iconColor: MichiPalette.auroraCyan
                        strokeWidth: 1.6
                    }
                }
                ColumnLayout {
                    visible: !root.compact
                    spacing: 0
                    MichiText {
                        text: "Michi"
                        role: "section"
                        color: MichiPalette.textPrimary
                    }
                    MichiText {
                        text: "LOCAL HI-FI"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
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

        MichiGlassSurface {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.preferredHeight: 94
            Layout.topMargin: MichiSpacing.lg
            elevation: "subtle"
            contentPadding: MichiSpacing.md
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
                        width: 7
                        height: 7
                        radius: 4
                        color: library.fileCount > 0
                            ? MichiPalette.auroraGreen : MichiPalette.textMuted
                    }
                    MichiText {
                        text: "LOCAL LIBRARY"
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                    }
                    Item { Layout.fillWidth: true }
                }
                MichiText {
                    text: library.fileCount > 0
                        ? library.fileCount + " tracks" : "Ready to scan"
                    role: "body"
                    font.weight: Font.DemiBold
                }
                MichiText {
                    text: library.fileCount > 0
                        ? library.albumCount + " albums · "
                            + library.artistCount + " artists"
                        : "Your collection stays on this device"
                    role: "caption"
                    color: MichiPalette.textMuted
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
        Item { Layout.fillHeight: true }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: MichiSemanticColors.borderSubtle }
        Repeater {
            model: root._bottom_routes
            delegate: routeDelegate
        }
    }
}
