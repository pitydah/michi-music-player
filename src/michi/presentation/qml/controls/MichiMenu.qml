import QtQuick
import QtQuick.Controls.Basic
import "../primitives"
import "../theme"

Menu {
    id: root
    padding: MichiSpacing.xs
    // Consistent with the popup family: fade + subtle slide, outCubic
    enter: Transition {
        NumberAnimation {
            property: "opacity"; from: 0; to: 1
            duration: MichiMotion.panel
            easing.type: MichiMotion.outCubic
        }
        NumberAnimation {
            property: "y"; from: -6; to: 0
            duration: MichiMotion.panel
            easing.type: MichiMotion.outCubic
        }
    }
    exit: Transition {
        NumberAnimation {
            property: "opacity"; from: 1; to: 0
            duration: MichiMotion.standard
            easing.type: MichiMotion.outCubic
        }
    }
    delegate: MenuItem {
        id: menuItem
        implicitHeight: MichiMetrics.controlMedium
        leftPadding: MichiSpacing.md
        rightPadding: MichiSpacing.md
        contentItem: MichiText {
            text: menuItem.text
            role: "secondary"
            color: menuItem.enabled ? MichiPalette.textPrimary : MichiPalette.textDisabled
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: MichiRadius.sm
            color: menuItem.down ? MichiSemanticColors.surfacePressed
                : menuItem.highlighted ? MichiSemanticColors.surfaceHover : "transparent"
            HoverHandler { cursorShape: Qt.PointingHandCursor }
        }
    }
    background: MichiGlassSurface { elevation: "elevated"; contentPadding: 0; radius: MichiRadius.md }
}
