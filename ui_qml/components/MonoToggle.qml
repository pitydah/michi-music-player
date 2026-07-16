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

    objectName: "monoToggle"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Control de mono"

    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        spacing: MichiTheme.spacing.sm

        Text {
            text: "Mono"
            color: MichiTheme.colors.textNormal
            font.pixelSize: MichiTheme.typography.bodySize
            Accessible.name: "Alternar mono"
        }

        Switch {
            id: monoSwitch
            checked: root.monoEnabled
            objectName: "monoSwitch"
            Accessible.name: "Alternar mono"
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
