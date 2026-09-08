import QtQuick
import QtQuick.Controls.Basic
import "../theme"

// R11 NAV-01..04 (§5C): el scrollbar compartido de Library — hitbox
// cómoda (12px) con thumb visual fino, mínimo de tamaño para listas
// enormes y un thumb idle visible pero discreto (nunca desaparecido).
ScrollBar {
    id: root

    policy: ScrollBar.AsNeeded
    interactive: true
    hoverEnabled: true
    minimumSize: 0.04

    // Attached vertical bars consume implicitWidth; horizontal bars consume
    // implicitHeight. Keep a comfortable mouse hitbox without heavy chrome.
    implicitWidth: root.vertical ? 12 : 48
    implicitHeight: root.horizontal ? 12 : 48
    padding: 3

    contentItem: Rectangle {
        implicitWidth: root.vertical ? 6 : 36
        implicitHeight: root.horizontal ? 6 : 36
        radius: 3

        color: root.pressed
            ? MichiPalette.auroraCyan
            : root.hovered
                ? MichiPalette.textSecondary
                : MichiPalette.textMuted

        opacity: root.size >= 1.0
            ? 0
            : root.pressed
                ? 1.0
                : root.hovered
                    ? 0.92
                    : root.active
                        ? 0.72
                        : 0.27

        Behavior on opacity {
            enabled: !MichiAccessibility.reducedMotion
            NumberAnimation {
                duration: MichiMotion.standard
                easing.type: MichiMotion.outCubic
            }
        }

        Behavior on color {
            enabled: !MichiAccessibility.reducedMotion
            ColorAnimation { duration: MichiMotion.micro }
        }
    }

    background: Rectangle {
        radius: 4
        color: MichiSemanticColors.controlSurface
        opacity: root.size < 1.0
            ? (root.hovered || root.pressed ? 0.30 : 0.10)
            : 0
    }
}
