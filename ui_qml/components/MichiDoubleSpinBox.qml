import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../theme"

Item {
    id: root

    property string controlObjectName: ""
    objectName: controlObjectName

    property real from: 0
    property real to: 100
    property real value: 0
    property real stepSize: 0.1
    property int decimals: 1
    property bool loading: false
    property string accessibleName: "Valor: " + root._formatValue(root.value)
    property string accessibleDescription: ""

    signal valueModified()

    implicitWidth: 160
    implicitHeight: MichiTheme.minimumInteractiveSize
    activeFocusOnTab: enabled && visible

    Accessible.role: Accessible.Pane
    Accessible.name: root.accessibleName
    Accessible.description: root.accessibleDescription

    function _formatValue(v) {
        return Number(v).toFixed(root.decimals)
    }

    RowLayout {
        anchors.fill: parent
        spacing: 2

        MichiButton {
            objectName: "michiDoubleSpinBoxDecrement"
            text: qsTr("-")
            implicitWidth: 32
            implicitHeight: parent.height
            variant: "ghost"
            enabled: root.enabled && !root.loading
            onClicked: {
                var next = Math.max(root.from, root.value - root.stepSize)
                next = Math.round(next / root.stepSize) * root.stepSize
                if (next !== root.value) {
                    root.value = next
                    root.valueModified()
                }
            }
        }

        QQC2.TextField {
            id: field
            objectName: "michiDoubleSpinBoxField"
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root._formatValue(root.value)
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: MichiTheme.typography.bodySize
            color: MichiTheme.colors.textPrimary
            enabled: root.enabled && !root.loading
            activeFocusOnTab: enabled && visible
            background: Rectangle {
                color: MichiTheme.colors.surfaceInput
                radius: MichiTheme.radius.sm
                border.width: field.activeFocus ? MichiTheme.focusWidth : MichiTheme.borderWidth
                border.color: field.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
            }
            validator: IntValidator {
                bottom: root.from * 100
                top: root.to * 100
            }
            onEditingFinished: {
                var v = parseInt(text) / 100
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
            Keys.onUpPressed: function(event) {
                var next = Math.min(root.to, root.value + root.stepSize)
                next = Math.round(next / root.stepSize) * root.stepSize
                if (next !== root.value) {
                    root.value = next
                    root.valueModified()
                }
                event.accepted = true
            }
            Keys.onDownPressed: function(event) {
                var next = Math.max(root.from, root.value - root.stepSize)
                next = Math.round(next / root.stepSize) * root.stepSize
                if (next !== root.value) {
                    root.value = next
                    root.valueModified()
                }
                event.accepted = true
            }
        }

        MichiButton {
            objectName: "michiDoubleSpinBoxIncrement"
            text: qsTr("+")
            implicitWidth: 32
            implicitHeight: parent.height
            variant: "ghost"
            enabled: root.enabled && !root.loading
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
