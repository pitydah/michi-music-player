import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property bool bridgeAvailable: root.jobBr !== null

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    objectName: "AudioBatchJobsPage"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    objectName: "audioJobs.page"
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
        objectName: "audioJobs.focusScope"
=======
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Text {
                text: "Trabajos de Audio Lab"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "jobsPageTitle"
            }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
>>>>>>> Stashed changes

            Text {
                text: "Cola, activos, historial, progreso por archivo, velocidad, ETA, reintentos, cancelación"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "jobsPageSubtitle"
            }

<<<<<<< Updated upstream
=======
                Text {
                    text: "Trabajos de Audio Lab"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Trabajos de Audio Lab"
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                }

            SectionHeader { text: "Trabajos activos"; width: parent.width; objectName: "jobsActiveHeader"; Accessible.name: "Trabajos activos" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "queued" || j.state === "running" || j.state === "cancel_requested" }) : []
=======
>>>>>>> origin/michi-qml-functional-wave
                }

=======
>>>>>>> origin/michi-qml-functional-wave
                }

>>>>>>> Stashed changes
<<<<<<< HEAD
                Text {
                    text: "Cola, progreso, cancelar, reintentar. Trabajos completados y fallidos."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }
>>>>>>> Stashed changes

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: modelData.state === "failed" ? "danger" : modelData.state === "completed" ? "success" : "base"
                    objectName: "activeJobItem_" + index
                    Accessible.name: modelData.title || "Trabajo activo"
                    Row {
<<<<<<< Updated upstream
=======
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: root.jobBr ? root.jobBr.activeCount : "0"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                            Text { text: "Activos"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: root.jobBr ? root.jobBr.jobs.length : "0"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                            Text { text: "Total"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }
=======
            SectionHeader { text: "Trabajos activos"; width: parent.width; objectName: "jobsActiveHeader"; Accessible.name: "Trabajos activos" }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "queued" || j.state === "running" || j.state === "cancel_requested" }) : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: modelData.state === "failed" ? "danger" : modelData.state === "completed" ? "success" : "base"
                    objectName: "activeJobItem_" + index
                    Accessible.name: modelData.title || "Trabajo activo"
                    Row {
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
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
=======
>>>>>>> origin/michi-qml-functional-wave
                    }
                }

=======
>>>>>>> origin/michi-qml-functional-wave
                    }
                }

>>>>>>> Stashed changes
<<<<<<< HEAD
                SectionHeader { text: "En ejecución / En cola"; width: parent.width; objectName: "jobs.section.active" }

                Repeater {
                    id: activeRepeater
                    model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "queued" || j.state === "running" || j.state === "cancel_requested" }) : []

                    delegate: GlassMaterial {
                        width: parent.width; radius: MichiTheme.radiusSm; variant: modelData.state === "running" ? "accent" : "base"
                        objectName: "jobs.activeItem." + modelData.job_id
                        height: 56
                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                            Text { width: parent.width * 0.25; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                            Text { width: parent.width * 0.12; text: modelData.state || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            Text { width: parent.width * 0.12; text: modelData.progress ? Math.round(modelData.progress * 100) + "%" : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            MichiProgressBar {
                                width: parent.width * 0.18; anchors.verticalCenter: parent.verticalCenter
                                value: modelData.progress || 0; from: 0; to: 1
                                visible: modelData.state === "running"
                            }
                            MichiButton {
                                width: 60; height: 24; text: modelData.state === "running" ? "Cancelar" : "Cancelar"; variant: "danger"
                                objectName: "jobs.cancelBtn." + modelData.job_id
                                anchors.verticalCenter: parent.verticalCenter
                                enabled: modelData.state !== "cancel_requested"
                                onClicked: root.cancelJob(modelData.job_id)
                                Accessible.name: "Cancelar trabajo " + modelData.title
                            }
                        }
                    }
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
                SectionHeader { text: "Fallidos"; width: parent.width; objectName: "jobs.section.failed" }

                Repeater {
                    model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "failed" || j.state === "cancelled" }) : []
                    delegate: GlassMaterial {
                        width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: "danger"
                        objectName: "jobs.failedItem." + modelData.job_id
                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                            Text { width: parent.width * 0.40; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                            Text { width: parent.width * 0.25; text: (modelData.error_code || modelData.state || ""); color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                            MichiButton {
                                width: 50; height: 24; text: "Reintentar"; variant: "secondary"
                                objectName: "jobs.retryBtn." + modelData.job_id
                                anchors.verticalCenter: parent.verticalCenter
                                visible: modelData.state === "failed"
                                onClicked: root.retryJob(modelData.job_id)
                                Accessible.name: "Reintentar trabajo " + modelData.title
                            }
                        }
                    }
                }

                EmptyState {
                    width: parent.width
                    iconText: ""
                    title: "Sin trabajos fallidos"
                    subtitle: ""
                    visible: root.jobBr && root.jobBr.jobs.filter(function(j) { return j.state === "failed" }).length === 0
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: "Limpiar completados"; variant: "secondary"
                        objectName: "jobs.clearCompletedBtn"
                        enabled: root.jobBr && root.jobBr.jobs.filter(function(j) { return j.state === "completed" }).length > 0
                        onClicked: { if (root.jobBr) root.jobBr.clearCompleted() }
                        Accessible.name: "Limpiar trabajos completados"
                    }
                    MichiButton {
                        text: "Limpiar fallidos"; variant: "danger"
                        objectName: "jobs.clearFailedBtn"
                        enabled: root.jobBr && root.jobBr.jobs.filter(function(j) { return j.state === "failed" || j.state === "cancelled" }).length > 0
                        onClicked: { if (root.jobBr) root.jobBr.clearFailed() }
                        Accessible.name: "Limpiar trabajos fallidos"
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "jobs.backBtn"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            StatusBadge {
                visible: root.jobBr === null
                text: "Bridge de trabajos no disponible"
                kind: "disconnected"
                objectName: "jobsBridgeStatus"
                Accessible.name: "Bridge de trabajos no disponible"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }
}
