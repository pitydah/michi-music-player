import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    objectName: "AudioBatchJobsPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Trabajos de Audio Lab"

    function _cancelJob(jobId) {
        if (root.jobBr && root.jobBr.cancelJob)
            root.jobBr.cancelJob(jobId)
    }

    function _retryJob(jobId) {
        if (root.jobBr && root.jobBr.retryJob)
            root.jobBr.retryJob(jobId)
    }

    function _viewJob(jobData) {
        if (root.nav)
            root.nav.navigateWithParams("audio_lab_job_detail", { job: jobData })
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Trabajos de Audio Lab"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "jobsPageTitle"
            }

            Text {
                text: "Cola, activos, historial, progreso por archivo, velocidad, ETA, reintentos, cancelación"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "jobsPageSubtitle"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                objectName: "jobsSummary"
                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.jobBr ? root.jobBr.activeCount : "0"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Activos"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.jobBr ? root.jobBr.jobs.length : "0"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Total"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                }
            }

            SectionHeader { text: "Trabajos activos"; width: parent.width; objectName: "jobsActiveHeader"; Accessible.name: "Trabajos activos" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "queued" || j.state === "running" || j.state === "cancel_requested" }) : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: modelData.state === "failed" ? "danger" : modelData.state === "completed" ? "success" : "base"
                    objectName: "activeJobItem_" + index
                    Accessible.name: modelData.title || "Trabajo activo"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.30; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.15; text: modelData.state || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.10; text: modelData.progress ? Math.round(modelData.progress * 100) + "%" : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        MichiButton { width: 50; height: 24; text: "Cancelar"; variant: "danger"; anchors.verticalCenter: parent.verticalCenter; visible: modelData.state === "running" || modelData.state === "queued"; objectName: "cancelJobBtn_" + index; Accessible.name: "Cancelar trabajo"; activeFocusOnTab: true; Keys.onReturnPressed: onClicked(); Keys.onSpacePressed: onClicked(); onClicked: root._cancelJob(modelData.job_id) }
                        MichiButton { width: 40; height: 24; text: "Ver"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter; objectName: "viewJobBtn_" + index; Accessible.name: "Ver detalle"; activeFocusOnTab: true; Keys.onReturnPressed: onClicked(); Keys.onSpacePressed: onClicked(); onClicked: root._viewJob(modelData) }
                    }
                }
            }

            SectionHeader { text: "Completados"; width: parent.width; objectName: "jobsCompletedHeader"; Accessible.name: "Trabajos completados" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "completed" || j.state === "completed_with_errors" }) : []

                GlassMaterial {
                    width: parent.width; height: 40; radius: MichiTheme.radiusSm; variant: modelData.state === "completed_with_errors" ? "warning" : "base"
                    objectName: "completedJobItem_" + index
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.30; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.15; text: modelData.state === "completed" ? "Completado" : "Con errores"; color: modelData.state === "completed" ? MichiTheme.colors.success : MichiTheme.colors.warning; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.20; text: modelData.duration ? Math.round(modelData.duration) + "s" : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            SectionHeader { text: "Fallidos"; width: parent.width; objectName: "jobsFailedHeader"; Accessible.name: "Trabajos fallidos" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "failed" }) : []

                GlassMaterial {
                    width: parent.width; height: 40; radius: MichiTheme.radiusSm; variant: "danger"
                    objectName: "failedJobItem_" + index
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.30; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.15; text: modelData.error_code || "ERROR"; color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        MichiButton { width: 55; height: 24; text: "Reintentar"; variant: "secondary"; anchors.verticalCenter: parent.verticalCenter; objectName: "retryJobBtn_" + index; Accessible.name: "Reintentar trabajo"; activeFocusOnTab: true; Keys.onReturnPressed: onClicked(); Keys.onSpacePressed: onClicked(); onClicked: root._retryJob(modelData.job_id) }
                    }
                }
            }

            SectionHeader { text: "Cancelados"; width: parent.width; objectName: "jobsCancelledHeader"; Accessible.name: "Trabajos cancelados" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "cancelled" }) : []

                GlassMaterial {
                    width: parent.width; height: 36; radius: MichiTheme.radiusSm; variant: "base"
                    objectName: "cancelledJobItem_" + index
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.50; text: modelData.title || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "Cancelado"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Limpiar completados"
                    variant: "secondary"
                    objectName: "clearCompletedBtn"
                    Accessible.name: "Limpiar trabajos completados"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.jobBr) root.jobBr.clearCompleted() }
                }
                MichiButton {
                    text: "Limpiar fallidos"
                    variant: "danger"
                    objectName: "clearFailedBtn"
                    Accessible.name: "Limpiar trabajos fallidos"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.jobBr) root.jobBr.clearFailed() }
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "jobsBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            StatusBadge {
                visible: root.jobBr === null
                text: "Bridge de trabajos no disponible"
                kind: "disconnected"
                objectName: "jobsBridgeStatus"
                Accessible.name: "Bridge de trabajos no disponible"
            }
        }
    }
}
