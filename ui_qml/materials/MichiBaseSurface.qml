import QtQuick
import "../theme"

/* Michi Music Player — Base Surface
 *
 * Canonical surface component for the visual hierarchy:
 *   level1:  #0E141E  — background surfaces (sidebar, panels)
 *   level2:  #121A26  — elevated surfaces (cards, popups)
 *   level3:  #172131  — interactive surfaces (buttons, inputs)
 *   level4:  #1C283A  — highest elevation (modals, tooltips)
 *
 * Properties:
 *   level       — surface elevation (1-4)
 *   radius      — corner radius (default: 8px)
 *   border      — show subtle border (default: true)
 *   selected    — show accent border (default: false)
 *   hovered     — show hover state (default: false)
 *   glow        — show accent glow (default: false)
 */

Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.ignored: true

    property int level: 1
    property int radius: MichiTheme.radius.md
    property bool borderVisible: true
    property bool selected: false
    property bool hovered: false
    property bool glow: false

    default property alias content: contentLayer.data

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: {
            if (root.level >= 4) return MichiTheme.colors.surfaceElevation4
            if (root.level >= 3) return MichiTheme.colors.surfaceElevation3
            if (root.level >= 2) return MichiTheme.colors.surfaceElevation2
            return MichiTheme.colors.surfaceElevation1
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root.hovered
            color: MichiTheme.colors.surfaceCardHover
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root.glow
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.accentGlow }
                GradientStop { position: 1.0; color: Qt.rgba(0.561, 0.718, 1.0, 0.0) }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root.borderVisible
            border.width: root.selected ? MichiTheme.borderWidth * 2 : MichiTheme.borderWidth
            border.color: root.selected ? MichiTheme.colors.accentPrimary : MichiTheme.colors.borderSubtle
            color: "transparent"
        }
    }

    Item {
        id: contentLayer
        anchors.fill: parent
        anchors.margins: root.level >= 3 ? MichiTheme.spacing.xs : 0
    }
}
