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
    spacing: 0
    signal configurationRequested(string action)

    Repeater {
        model: root.stages
        delegate: MichiSignalNode {
            required property var modelData
            required property int index
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
            iconName: modelData.id === "source" ? "track"
                : modelData.id === "decode" ? "audio-engine"
                : modelData.id === "processing" ? "equalizer"
                : modelData.id === "resample" ? "sliders"
                : modelData.id === "channel-remap" ? "audio-output"
                : modelData.id === "fir" ? "equalizer"
                : modelData.id === "output" ? "audio-output"
                : "device"
            title: modelData.title || ""
            summary: modelData.summary || ""
            detail: modelData.detail || ""
            detailRows: modelData.detailRows || []
            // DAC compact inspector has no navigation callback; never render a
            // dead configuration button in that variant.
            configAction: root.compact ? "NONE" : (modelData.configAction || "NONE")
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
