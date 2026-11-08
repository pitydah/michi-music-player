import QtQuick
import QtQuick.Layouts
import "../theme"

// A48: passive metrics disclosure within the SINGLE Signal Truth inspector.
// No audio observation, timer, polling, claim inference or DSP mutations here.
// metricItems must come from an already certified/read-only worker projection.
ColumnLayout {
    id: root
    objectName: "michiSignalTruthMetricsA48"
    property var metricItems: []
    property bool compact: false
    property string temporalStatus: "NONE"
    spacing: MichiSpacing.sm

    readonly property var metricIds: [
        "sample_peak_dbfs", "true_peak_dbtp", "integrated_lufs",
        "clipped_samples", "xrun_events", "processing_speed",
        "owner_to_ui_ms", "frame_dispatch_ms", "projection_build_ms"
    ]

    function safeMetricTitle(id) {
        if (id === "sample_peak_dbfs") return qsTr("Sample peak")
        if (id === "true_peak_dbtp") return qsTr("True peak")
        if (id === "integrated_lufs") return qsTr("Integrated loudness")
        if (id === "clipped_samples") return qsTr("Clipped samples")
        if (id === "xrun_events") return qsTr("Output XRUN")
        if (id === "processing_speed") return qsTr("DSP processing speed")
        if (id === "owner_to_ui_ms") return qsTr("Owner to UI latency")
        if (id === "frame_dispatch_ms") return qsTr("UI frame dispatch")
        if (id === "projection_build_ms") return qsTr("Signal Truth projection time")
        return qsTr("Unknown metric")
    }

    function safeMetricValue(item) {
        if (!item || (item.state !== "OBSERVED" && item.state !== "PARTIAL"))
            return qsTr("Not observed")
        if (root.metricIds.indexOf(item.name) < 0 ||
                typeof item.value !== "number" || !isFinite(item.value))
            return qsTr("Not observed")
        const value = item.value.toFixed(2)
        if (item.name === "sample_peak_dbfs") return value + " dBFS"
        if (item.name === "true_peak_dbtp") return value + " dBTP"
        if (item.name === "integrated_lufs") return value + " LUFS"
        if (item.name === "clipped_samples") return String(Math.floor(item.value))
        if (item.name === "xrun_events") return String(Math.floor(item.value))
        if (item.name === "processing_speed") return value + "×"
        return value + " ms"
    }

    Repeater {
        model: root.temporalStatus === "ACTIVE" && root.metricItems
            ? root.metricItems.slice(0, 8) : []
        delegate: RowLayout {
            required property var modelData
            objectName: "signalTruthMetricRow"
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            readonly property string metricValue: root.safeMetricValue(modelData)
            Accessible.role: Accessible.StaticText
            Accessible.name: root.safeMetricTitle(modelData.name) + ": " + metricValue
            Text {
                text: root.safeMetricTitle(modelData.name)
                color: MichiPalette.textSecondary
                font.pixelSize: root.compact ? 11 : 12
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Text {
                text: metricValue + (modelData.state === "PARTIAL" ? qsTr(" · partial") : "")
                color: modelData.state === "PARTIAL"
                    ? MichiPalette.textSecondary : MichiPalette.textPrimary
                font.pixelSize: root.compact ? 11 : 12
            }
        }
    }
}
