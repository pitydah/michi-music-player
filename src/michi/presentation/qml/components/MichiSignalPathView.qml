import QtQuick
import QtQuick.Layouts
import "../theme"

// Single visual grammar for Signal Truth. Popup and DAC diagnostics both feed
// it a read-only stage projection; this component owns no audio semantics.
ColumnLayout {
    id: root
    property var stages: []
    property string expandedStageId: ""
    property bool compact: false
    // DAC diagnostics stays read-only, while short Signal Truth windows
    // keep their genuine configuration actions.
    property bool configurationEnabled: !compact
    spacing: 0
    signal configurationRequested(string action)

    function focusFirstStage() {
        for (let index = 0; index < children.length; index += 1) {
            if (children[index].activeFocusOnTab) {
                children[index].forceActiveFocus()
                return
            }
        }
    }

    Repeater {
        model: root.stages
        delegate: MichiSignalNode {
            required property var modelData
            required property int index
            objectName: "signalStage_" + modelData.id
            Layout.fillWidth: true
            stageIndex: index
            stageCount: root.stages.length
            compact: root.compact
            first: modelData.first !== undefined ? modelData.first : index === 0
            last: modelData.last !== undefined ? modelData.last
                : index === root.stages.length - 1
            expanded: root.expandedStageId === modelData.id
            expandable: modelData.expandable !== undefined
                ? modelData.expandable
                : (modelData.detail || "").length > 0
            iconName: modelData.id === "source" ? "file-music"
                : modelData.id === "decode" ? "cpu"
                : modelData.id === "processing" ? "adjustments-horizontal"
                : modelData.id === "resample" ? "arrows-exchange"
                : modelData.id === "channel-remap" ? "arrows-exchange"
                : modelData.id === "fir" ? "adjustments-horizontal"
                : modelData.id === "output" ? "wave-sine"
                : "circuit-diode"
            title: modelData.title || ""
            summary: modelData.summary || ""
            detail: modelData.detail || ""
            detailRows: modelData.detailRows || []
            // Navigation is a capability, not a side effect of density.
            configAction: root.configurationEnabled
                ? (modelData.configAction || "NONE") : "NONE"
            stageState: modelData.state || "unknown"
            onToggleRequested: {
                root.expandedStageId = root.expandedStageId === modelData.id
                    ? "" : modelData.id
            }
            onConfigurationRequested: action => {
                root.configurationRequested(action)
            }
        }
    }
}
