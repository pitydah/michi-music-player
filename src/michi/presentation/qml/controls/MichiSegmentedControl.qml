import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root
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
            model: root.model
            delegate: MichiButton {
                required property var modelData
                objectName: root.objectName.length > 0
                    ? root.objectName + "-" + modelData.value : ""
                Layout.fillHeight: true
                text: root.compact ? "" : modelData.label
                iconName: modelData.icon || ""
                iconOnly: root.compact
                accessibleName: (root.accessiblePrefix.length > 0
                    ? root.accessiblePrefix + ": " : "") + modelData.label
                variant: "ghost"
                selected: root.currentValue === modelData.value
                onClicked: root.selected(modelData.value)
            }
        }
    }
}
