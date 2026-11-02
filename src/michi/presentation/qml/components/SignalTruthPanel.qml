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
    property string expandedStageId: ""
    spacing: MichiSpacing.xs

    RowLayout {
        Layout.fillWidth: true
        MichiText {
            Layout.fillWidth: true
            text: qsTr("Signal Truth")
            role: "section"
            font.weight: Font.DemiBold
        }
        MichiStatusChip {
            text: root.verdictLabel
            tone: root.verdictLabel === "Output mismatch" ? "error" : "neutral"
        }
    }

    MichiSignalPathView {
        Layout.fillWidth: true
        stages: root.stages
        expandedStageId: root.expandedStageId
        compact: true
        onConfigurationRequested: root.expandedStageId = ""
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
