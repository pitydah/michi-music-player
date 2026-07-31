import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Interruptor de movimiento reducido")
    objectName: "reducedMotionToggle"
    focus: true
    id: root

    property bool reduceMotion: false
    property var themeBridge: null

    signal reduceMotionToggled(bool enabled)



    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        spacing: MichiTheme.spacing.sm

        Text {
            text: qsTr("Reducir movimiento")
            color: MichiTheme.colors.textNormal
            font.pixelSize: MichiTheme.typography.bodySize
        }

        Switch {
            Accessible.role: Accessible.CheckBox

            Accessible.name: qsTr("Interruptor")

            Accessible.checked: root.checked

            id: motionSwitch
            activeFocusOnTab: true

            checked: root.reduceMotion
            Accessible.onPressAction: toggle()

            onToggled: {
                root.reduceMotion = checked
                if (root.themeBridge && typeof root.themeBridge.reducedMotion !== "undefined")
                    root.themeBridge.reducedMotion = checked
                root.reduceMotionToggled(checked)
            }
        }
    }
}
