import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Mono Toggle"
    objectName: "monoToggle"
    focus: true
    id: root

    property bool monoEnabled: false
    property var audioBridge: null

    signal monoToggled(bool enabled)



    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        spacing: MichiTheme.spacing.sm

        Text {
            text: qsTr("Mono")
            color: MichiTheme.colors.textNormal
            font.pixelSize: MichiTheme.typography.bodySize
        }

        Switch {
            Accessible.role: Accessible.CheckBox

            Accessible.name: "Switch"

            Accessible.checked: root.checked

            id: monoSwitch
            activeFocusOnTab: true

            checked: root.monoEnabled
            Accessible.onPressAction: toggle()

            onToggled: {
                root.monoEnabled = checked
                if (root.audioBridge && typeof root.audioBridge.setMono !== "undefined")
                    root.audioBridge.setMono(checked)
                root.monoToggled(checked)
            }
        }
    }
}
