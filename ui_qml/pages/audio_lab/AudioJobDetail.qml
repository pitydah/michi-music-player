import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var jobData: null
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
=======
    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    objectName: "AudioJobDetail"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Detalle de trabajo"

    visible: root.jobData !== null

    function _cancelJob() {
        if (root.jobBr && root.jobData && root.jobBr.cancelJob)
            root.jobBr.cancelJob(root.jobData.job_id)
    }

    function _retryJob() {
        if (root.jobBr && root.jobData && root.jobBr.retryJob)
            root.jobBr.retryJob(root.jobData.job_id)
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
            Text { text: root.jobData ? root.jobData.title : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
            Text { text: "Estado: " + (root.jobData ? root.jobData.state : ""); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: "Progreso: " + (root.jobData && root.jobData.progress ? Math.round(root.jobData.progress * 100) + "%" : "0%"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: "Error: " + (root.jobData ? (root.jobData.error_code || "") : ""); color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; visible: root.jobData && root.jobData.state === "failed" }
            Row { spacing: MichiTheme.spacing.sm
                MichiButton { text: "Reintentar"; variant: "secondary"; enabled: root.jobData && root.jobData.state === "failed"; onClicked: root.alab && root.alab.retryJob(root.jobData.job_id) }
                MichiButton { text: "Cancelar"; variant: "danger"; enabled: root.jobData && root.jobData.state === "running"; onClicked: root.alab && root.alab.cancelJob(root.jobData.job_id) }
                MichiButton { text: "Abrir output"; variant: "ghost"; onClicked: {} }
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Detalle del trabajo"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "jobDetailTitle"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root.jobData && root.jobData.state === "failed" ? "danger" : root.jobData && root.jobData.state === "completed" ? "success" : "base"
                objectName: "jobDetailPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Text {
                        text: root.jobData ? root.jobData.title : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                        objectName: "jobDetailTitleText"
                    }

                    Row {
                        width: parent.width; spacing: MichiTheme.spacing.xl
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: "Estado"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData ? root.jobData.state : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }
                        }
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: "Progreso"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData && root.jobData.progress ? Math.round(root.jobData.progress * 100) + "%" : "0%"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        }
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: "Duración"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData && root.jobData.duration ? Math.round(root.jobData.duration) + "s" : "—"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        }
                    }

                    MichiProgressBar {
                        width: parent.width
                        value: root.jobData && root.jobData.progress ? root.jobData.progress * 100 : 0
                        from: 0; to: 100
                        objectName: "jobDetailProgressBar"
                        Accessible.name: "Progreso del trabajo"
                    }

                    Text {
                        text: "Error: " + (root.jobData ? (root.jobData.error_code || "") : "")
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.jobData && root.jobData.state === "failed"
                        objectName: "jobDetailError"
                    }

                    Text {
                        text: root.jobData && root.jobData.message ? root.jobData.message : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        wrapMode: Text.WordWrap
                        width: parent.width
                        visible: text !== ""
                        objectName: "jobDetailMessage"
                    }

                    SectionHeader { text: "Archivos"; width: parent.width; objectName: "jobFilesHeader"; Accessible.name: "Archivos" }

                    Repeater {
                        model: root.jobData && root.jobData.files ? root.jobData.files : []

                        GlassMaterial {
                            width: parent.width; height: 32; radius: MichiTheme.radiusSm; variant: "base"
                            Row {
                                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                                Text {
                                    width: parent.width * 0.60; text: modelData.filepath || modelData.name || ""
                                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                }
                                StatusBadge {
                                    text: modelData.status || ""
                                    kind: modelData.status === "completed" ? "success" : modelData.status === "failed" ? "error" : modelData.status === "running" ? "active" : "info"
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.sm
                        MichiButton {
                            text: "Cancelar"
                            variant: "danger"
                            enabled: root.jobData && (root.jobData.state === "running" || root.jobData.state === "queued")
                            objectName: "jobDetailCancelBtn"
                            Accessible.name: "Cancelar trabajo"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root._cancelJob()
                        }
                        MichiButton {
                            text: "Reintentar"
                            variant: "secondary"
                            enabled: root.jobData && (root.jobData.state === "failed" || root.jobData.state === "cancelled")
                            objectName: "jobDetailRetryBtn"
                            Accessible.name: "Reintentar trabajo"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: root._retryJob()
                        }
                        MichiButton {
                            text: "Volver"
                            variant: "ghost"
                            objectName: "jobDetailBackBtn"
                            Accessible.name: "Volver"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: { if (root.nav) root.nav.back() }
                        }
                    }
                }
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
