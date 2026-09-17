pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    property string verdictLabel: qsTr("Not verified")
    property var stages: []
    property var reasonCodes: []
    spacing: MichiSpacing.xs

    RowLayout {
        Layout.fillWidth: true
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Signal Truth")
            role: "primary"
            font.weight: Font.DemiBold
        }
        MichiStatusChip {
            text: root.verdictLabel
            tone: root.verdictLabel === "Output mismatch" ? "error" : "neutral"
        }
    }

    Repeater {
        model: root.stages
        delegate: RowLayout {
            id: stage
            required property var modelData
            Layout.fillWidth: true
            MichiText {
                Layout.preferredWidth: 92
                text: stage.modelData.title
                role: "secondary"
            }
            MichiText {
                Layout.fillWidth: true
                text: stage.modelData.summary
                role: "technical"
                technical: true
                wrapMode: Text.Wrap
            }
        }
    }

    MichiText {
        visible: root.reasonCodes.length > 0
        Layout.fillWidth: true
        text: qsTr("Evidence reasons: %1").arg(root.reasonCodes.join(", "))
        role: "technical"
        technical: true
        wrapMode: Text.WordWrap
    }
}
