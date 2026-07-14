import QtQuick
import QtQuick.Controls
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property real from: 0
    property real to: 100
    property real value: 0
    property real stepSize: 0.1
    property int decimals: 1

    signal valueModified()

    implicitWidth: 160
    implicitHeight: MichiTheme.minimumInteractiveSize

    Accessible.role: Accessible.SpinBox
    Accessible.name: "Valor decimal"

    function _formatValue(v) {
        return Number(v).toFixed(root.decimals)
    }

    RowLayout {
        anchors.fill: parent
        spacing: 2

        MichiButton {
            text: "-"
            implicitWidth: 32
            implicitHeight: parent.height
            variant: "ghost"
            onClicked: {
                var next = Math.max(root.from, root.value - root.stepSize)
                next = Math.round(next / root.stepSize) * root.stepSize
                if (next !== root.value) {
                    root.value = next
                    root.valueModified()
                }
            }
        }

        TextField {
            id: field
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root._formatValue(root.value)
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: MichiTheme.typography.bodySize
            color: MichiTheme.colors.textPrimary
            background: Rectangle {
                color: MichiTheme.colors.surfaceInput
                radius: MichiTheme.radius.sm
                border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
            }
            validator: DoubleValidator {
                bottom: root.from
                top: root.to
                decimals: root.decimals
            }
            onEditingFinished: {
                var v = parseFloat(text)
                if (!isNaN(v)) {
                    v = Math.max(root.from, Math.min(root.to, v))
                    v = Math.round(v / root.stepSize) * root.stepSize
                    if (v !== root.value) {
                        root.value = v
                        root.valueModified()
                    }
                }
                text = root._formatValue(root.value)
            }
        }

        MichiButton {
            text: "+"
            implicitWidth: 32
            implicitHeight: parent.height
            variant: "ghost"
            onClicked: {
                var next = Math.min(root.to, root.value + root.stepSize)
                next = Math.round(next / root.stepSize) * root.stepSize
                if (next !== root.value) {
                    root.value = next
                    root.valueModified()
                }
            }
        }
    }
}
