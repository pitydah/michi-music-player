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

    objectName: "audioJobs.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Trabajos de Audio Lab"

    function cancelJob(jobId) {
        if (root.jobBr) root.jobBr.cancelJob(jobId)
    }

    function retryJob(jobId) {
        if (root.jobBr) root.jobBr.retryJob(jobId)
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioJobs.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Trabajos de Audio Lab"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Trabajos de Audio Lab"
                }

                Text {
                    text: "Cola, progreso, cancelar, reintentar. Trabajos completados y fallidos."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                    objectName: "jobs.summary"
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
                }

                EmptyState {
                    width: parent.width
                    iconText: ""
                    title: "Sin trabajos activos"
                    subtitle: "Los trabajos de conversión y análisis aparecerán aquí"
                    visible: root.jobBr && root.jobBr.jobs.filter(function(j) { return j.state === "queued" || j.state === "running" }).length === 0
                }

                SectionHeader { text: "Completados"; width: parent.width; objectName: "jobs.section.completed" }

                Repeater {
                    model: root.jobBr ? root.jobBr.jobs.filter(function(j) { return j.state === "completed" }) : []
                    delegate: GlassMaterial {
                        width: parent.width; height: 44; radius: MichiTheme.radiusSm; variant: "success"
                        objectName: "jobs.completedItem." + modelData.job_id
                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                            Text { width: parent.width * 0.60; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                            Text { text: "Completado"; color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }
                }

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
            }
        }
    }
}
