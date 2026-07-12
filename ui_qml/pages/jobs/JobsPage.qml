import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var bridge: typeof jobBridge !== "undefined" ? jobBridge : null

    function refresh() { if (root.bridge) root.bridge.jobsChanged }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Trabajos"; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary }
            Item { Layout.fillWidth: true }
            Label { text: root.bridge ? root.bridge.activeCount + " activos" : ""; color: MichiTheme.colors.textSecondary }
            MichiButton { text: "Limpiar completados"; variant: "ghost"; onClicked: { if (root.bridge) root.bridge.clearCompleted() } }
        }
        ListView {
            id: jobList; Layout.fillWidth: true; Layout.fillHeight: true
            model: root.bridge ? root.bridge.jobs : []; clip: true; spacing: 2
            delegate: Rectangle {
                width: jobList.width; height: 56; color: MichiTheme.colors.surfaceCard; radius: MichiTheme.radius.sm
                RowLayout {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Label { text: modelData.title || ""; font.weight: MichiTheme.typography.weightMedium; color: MichiTheme.colors.textPrimary; elide: Text.ElideRight }
                        Label { text: modelData.state || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.captionSize }
                        Label { text: modelData.message || ""; visible: modelData.message; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }
                    }
                    ProgressBar { value: modelData.progress || 0; from: 0; to: 1; width: 80; visible: modelData.state === "running" }
                    MichiButton { text: "Cancelar"; variant: "ghost"; visible: modelData.canCancel; onClicked: { if (root.bridge) root.bridge.cancelJob(modelData.job_id) } }
                    MichiButton { text: "Reintentar"; variant: "ghost"; visible: modelData.canRetry; onClicked: { if (root.bridge) root.bridge.retryJob(modelData.job_id) } }
                }
            }
            Item { anchors.centerIn: parent; visible: jobList.count === 0
                Label { text: "Sin trabajos"; color: MichiTheme.colors.textSecondary }
            }
        }
    }
}
