import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property var model: []
    property string currentValue: ""
    property bool compact: false
    signal selected(string value)
    implicitHeight: MichiMetrics.controlMedium
    implicitWidth: segments.implicitWidth + MichiSpacing.xs * 2
    radius: MichiRadius.md
    color: MichiSemanticColors.controlSurface
    border.width: 1
    border.color: MichiSemanticColors.borderSubtle

    RowLayout {
        id: segments
        anchors.fill: parent
        anchors.margins: MichiSpacing.xs
        spacing: MichiSpacing.xxs
        Repeater {
            model: root.model
            delegate: MichiButton {
                required property var modelData
                Layout.fillHeight: true
                text: root.compact ? "" : modelData.label
                iconName: modelData.icon || ""
                variant: "ghost"
                selected: root.currentValue === modelData.value
                Accessible.name: modelData.label
                onClicked: {
                    root.currentValue = modelData.value
                    root.selected(modelData.value)
                }
            }
        }
    }
}
