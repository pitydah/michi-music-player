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

    readonly property var _routes: [
        { id: "now_playing", label: "Now Playing", icon: "play" },
        { id: "library", label: "Library", icon: "library" },
        { id: "queue", label: "Queue", icon: "queue" }
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
                    visible: routeItem._active
                    Layout.preferredWidth: 2
                    Layout.preferredHeight: 20
                    radius: 2
                    color: MichiPalette.auroraBlue
                }
                MichiIcon {
                    Layout.leftMargin: routeItem._active ? MichiSpacing.sm : MichiSpacing.md
                    name: modelData.icon
                    Layout.preferredWidth: MichiMetrics.iconMedium
                    Layout.preferredHeight: MichiMetrics.iconMedium
                    iconColor: routeItem._active ? MichiPalette.auroraBlue
                        : routeItem.hovered ? MichiPalette.textPrimary : MichiPalette.textSecondary
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
                border.color: Qt.rgba(0.298, 0.651, 1, 0.18)
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
            Layout.preferredHeight: 54
            MichiText {
            anchors.centerIn: parent
                text: root.compact ? "M" : "Michi"
                role: "section"
                color: MichiPalette.textPrimary
            }
        }

        Repeater {
            model: root._routes
            delegate: routeDelegate
        }
        Item { Layout.fillHeight: true }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: MichiSemanticColors.borderSubtle }
        Repeater {
            model: root._bottom_routes
            delegate: routeDelegate
        }
    }
}
