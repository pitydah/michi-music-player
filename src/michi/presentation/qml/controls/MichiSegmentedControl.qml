import QtQuick
import QtQuick.Layouts
import "../theme"

Rectangle {
    id: segmentedControl
    property var model: []
    property string currentValue: ""
    property bool compact: false
    property string accessiblePrefix: ""
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
            model: segmentedControl.model
            delegate: MichiButton {
                required property var modelData
                objectName: segmentedControl.objectName.length > 0
                    ? segmentedControl.objectName + "-" + String(modelData.value) : ""
                Layout.fillHeight: true
                text: segmentedControl.compact ? "" : modelData.label
                iconName: modelData.icon || ""
                iconOnly: segmentedControl.compact
                iconSize: segmentedControl.compact ? 18 : MichiMetrics.iconSmall
                iconStrokeWidth: segmentedControl.compact ? 1.9 : 1.7
                accessibleName: (segmentedControl.accessiblePrefix.length > 0
                    ? segmentedControl.accessiblePrefix + ": " : "") + modelData.label
                variant: "ghost"
                selected: segmentedControl.currentValue === modelData.value
                onClicked: segmentedControl.selected(modelData.value)
            }
        }
    }
}
