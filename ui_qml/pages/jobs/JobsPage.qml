import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var bridge: typeof jobBridge !== "undefined" ? jobBridge : null
    property var jobListModel: null

    Component.onCompleted: {
        if (root.bridge && root.bridge.jobModel)
            root.jobListModel = root.bridge.jobModel
    }

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
            model: root.jobListModel ? root.jobListModel : (root.bridge ? root.bridge.jobs : [])
            clip: true; spacing: 2; boundsBehavior: Flickable.StopAtBounds

            delegate: Rectangle {
                width: jobList.width; height: 56
                color: MichiTheme.colors.surfaceCard; radius: MichiTheme.radius.sm
                Accessible.name: model.title || ""; Accessible.description: "Trabajo " + (model.state || "")

                RowLayout {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                        Label { text: model.title || ""; font.weight: MichiTheme.typography.weightMedium; color: MichiTheme.colors.textPrimary; elide: Text.ElideRight }
                        Label { text: model.state || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.captionSize }
                        Label { text: model.message || ""; visible: model.message; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }
                    }

                    ProgressBar { value: model.progress || 0; from: 0; to: 1; width: 80; visible: model.state === "running" }
                    MichiButton { text: "Cancelar"; variant: "ghost"; visible: model.canCancel; onClicked: { if (root.bridge) root.bridge.cancelJob(model.job_id) } }
                    MichiButton { text: "Reintentar"; variant: "ghost"; visible: model.canRetry; onClicked: { if (root.bridge) root.bridge.retryJob(model.job_id) } }
                }
            }

            MichiEmptyState {
                anchors.centerIn: parent; visible: jobList.count === 0
                title: "Sin trabajos"
            }

            MichiLoadingState {
                anchors.centerIn: parent; visible: root.bridge && root.bridge.activeCount > 0 && jobList.count === 0
            }
        }
    }
}
