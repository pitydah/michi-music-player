import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Reduced Motion Toggle"
    objectName: "reducedMotionToggle"
    focus: true
    id: root

    property bool reduceMotion: false
    property var themeBridge: null

    signal reduceMotionToggled(bool enabled)

    objectName: "reducedMotionToggle"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Reducir movimiento"

    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        spacing: MichiTheme.spacing.sm

        Text {
            text: "Reducir movimiento"
            color: MichiTheme.colors.textNormal
            font.pixelSize: MichiTheme.typography.bodySize
            Accessible.name: "Alternar reducción de movimiento"
        }

        Switch {
            id: motionSwitch
            checked: root.reduceMotion
            objectName: "reducedMotionSwitch"
            Accessible.name: "Reducir movimiento"
            Accessible.onPressAction: toggle()

            onToggled: {
                root.reduceMotion = checked
                if (root.themeBridge && typeof root.themeBridge.reduceMotion !== "undefined")
                    root.themeBridge.reduceMotion = checked
                root.reduceMotionToggled(checked)
            }
        }
    }
}
