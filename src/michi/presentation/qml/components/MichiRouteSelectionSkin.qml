import QtQuick
import "../theme"

// Shared non-interactive material skin for Engine and Output selection rows.
// Selection is preference; active is observed runtime; neither implies the other.
Rectangle {
    id: root
    property bool selected: false
    property bool active: false
    property bool hovered: false
    property bool pressed: false
    property bool visualFocus: false
    property bool available: true
    radius: MichiRadius.md
    color: "transparent"
    gradient: Gradient {
        GradientStop {
            position: 0
            color: root.active ? MichiSemanticColors.auroraCyanSurface
                : root.selected ? MichiSemanticColors.surfaceSelected
                : root.pressed ? MichiSemanticColors.surfacePressed
                : root.hovered ? MichiSemanticColors.surfaceHover
                : "transparent"
        }
        GradientStop {
            position: 1
            color: root.active ? MichiPalette.trackSurfaceBottom
                : root.selected ? MichiSemanticColors.controlSurface
                : root.pressed ? MichiSemanticColors.surfacePressed
                : root.hovered ? MichiSemanticColors.surfaceHover
                : "transparent"
        }
    }
    border.width: root.visualFocus || root.active || root.selected ? 1 : 0
    border.color: root.visualFocus ? MichiSemanticColors.focusRing
        : root.active ? MichiSemanticColors.auroraCyanBorderSubtle
        : root.selected ? MichiSemanticColors.auroraBorderSubtle
        : MichiSemanticColors.borderSubtle
    Rectangle {
        visible: root.active
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 9
        anchors.bottomMargin: 9
        width: 2
        radius: 1
        color: MichiPalette.auroraCyan
    }
}
