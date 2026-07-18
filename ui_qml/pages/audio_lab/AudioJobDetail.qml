import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Job Detail"
    focus: true
    id: root

    property var jobData: null
    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    objectName: "AudioJobDetail"

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
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: qsTr("Detalle del trabajo")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root.jobData && root.jobData.state === "failed" ? "danger" : root.jobData && root.jobData.state === "completed" ? "success" : "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Text {
                        text: root.jobData ? root.jobData.title : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Row {
                        width: parent.width; spacing: MichiTheme.spacing.xl
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: qsTr("Estado"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData ? root.jobData.state : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }
                        }
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: qsTr("Progreso"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData && root.jobData.progress ? Math.round(root.jobData.progress * 100) + "%" : qsTr("0%"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        }
                        Column { spacing: MichiTheme.spacing.xs
                            Text { text: qsTr("Duración"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                            Text { text: root.jobData && root.jobData.duration ? Math.round(root.jobData.duration) + "s" : qsTr("—"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                        }
                    }

                    MichiProgressBar {
                        Accessible.role: Accessible.ProgressBar

                        activeFocusOnTab: true

                        width: parent.width
                        value: root.jobData && root.jobData.progress ? root.jobData.progress * 100 : 0
                        from: 0; to: 100
                    }

                    Text {
                        text: qsTr("Error: ") + (root.jobData ? (root.jobData.error_code || "") : "")
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: root.jobData && root.jobData.state === "failed"
                    }

                    Text {
                        text: root.jobData && root.jobData.message ? root.jobData.message : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        wrapMode: Text.WordWrap
                        width: parent.width
                        visible: text !== ""
                    }

                    SectionHeader { text: qsTr("Archivos"); width: parent.width; objectName: "jobFilesHeader"; Accessible.name: "Archivos" }

                    Repeater {
                        model: root.jobData && root.jobData.files ? root.jobData.files : []

                        GlassMaterial {
                            width: parent.width; height: 32; radius: MichiTheme.radius.sm; variant: "base"
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
                            Accessible.role: Accessible.Button

                        spacing: MichiTheme.spacing.sm
                        MichiButton {
                            text: qsTr("Cancelar")
                            variant: "danger"
                            enabled: root.jobData && (root.jobData.state === "running" || root.jobData.state === "queued")
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            Accessible.role: Accessible.Button

                            onClicked: root._cancelJob()
                        }
                        MichiButton {
                            text: qsTr("Reintentar")
                            variant: "secondary"
                            enabled: root.jobData && (root.jobData.state === "failed" || root.jobData.state === "cancelled")
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Accessible.role: Accessible.Button

                            Keys.onSpacePressed: onClicked()
                            onClicked: root._retryJob()
                        }
                        MichiButton {
                            text: qsTr("Volver")
                            variant: "ghost"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: { if (root.nav) root.nav.back() }
                        }
                    }
                }
            }
        }
    }
}
