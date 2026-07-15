import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"
import "library_doctor"

Item {
    id: root

    objectName: "libraryDoctorPage"
    Accessible.role: Accessible.Pane
    Accessible.name: "Diagnóstico de biblioteca"

    property var doc: typeof libraryDoctorBridge !== "undefined" ? libraryDoctorBridge : null
    property string _state: "LOADING"
    property string _currentCategory: ""
    property int _scanProgress: 0
    property int _scanTotal: 0

    function _cap() { return root.doc !== null }

    Component.onCompleted: {
        if (root.doc && typeof root.doc.refresh !== "undefined") {
            root.doc.refresh()
            root._state = root.doc.status === "done" ? "READY" : "idle" ? "READY" : "READY"
        } else {
            root._state = "READY"
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true

        Keys.onEscapePressed: function(event) {
            if (root.doc && typeof root.doc.cancelScan !== "undefined")
                root.doc.cancelScan()
            event.accepted = true
        }

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Library Doctor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text { text: "Diagnóstico de biblioteca"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                    Text { text: "Analiza y detecta problemas en tu colección musical."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md
                Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                StatusBadge {
                    text: root.doc ? root.doc.status : "no disponible"
                    kind: root.doc && root.doc.status === "done" ? "success" :
                          root.doc && root.doc.status === "scanning" ? "warning" :
                          root.doc && root.doc.status === "repairing" ? "error" :
                          root.doc && root.doc.status === "error" ? "error" : "info"
                }
                StatusBadge {
                    text: "Solo lectura"
                    kind: "info"
                }
            }

            Row {
                spacing: MichiTheme.spacing.md
                visible: root.doc && root.doc.status === "done"
                Text { text: "Revisados: " + (root.doc ? root.doc.totalChecked : 0); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text { text: "Problemas: " + (root.doc ? root.doc.issueCount : 0); color: root.doc && root.doc.issueCount > 0 ? MichiTheme.colors.warning : MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.bodySize }
            }

            Row {
                spacing: MichiTheme.spacing.md
                visible: root.doc && root.doc.status === "done" && root.doc.issueCount > 0
                Text { text: "Metadata: " + (root.doc ? root.doc.missingMetadataCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                Text { text: "Archivos: " + (root.doc ? root.doc.missingFileCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                Text { text: "OK: " + (root.doc ? root.doc.healthyCount : 0); color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.metaSize }
            }

            Row {
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root._state === "SCANNING" ? "Escaneando..." : "Escanear biblioteca"
                    variant: "primary"
                    objectName: "doctorScanButton"
                    Accessible.name: "Iniciar escaneo de biblioteca"
                    enabled: root._state !== "SCANNING" && root._cap()
                    onClicked: {
                        if (root.doc && typeof root.doc.scan !== "undefined") {
                            root._state = "SCANNING"
                            root._scanProgress = 0
                            root._scanTotal = 0
                            root.doc.scan()
                            if (typeof notificationBridge !== "undefined" && notificationBridge)
                                notificationBridge.showMessage("Escaneando biblioteca...", "info")
                        }
                    }
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "doctorCancelButton"
                    Accessible.name: "Cancelar escaneo"
                    visible: root._state === "SCANNING"
                    onClicked: {
                        if (root.doc && typeof root.doc.cancelScan !== "undefined") {
                            root.doc.cancelScan()
                            root._state = "READY"
                        }
                    }
                }

                MichiButton {
                    text: "Refrescar"
                    variant: "ghost"
                    objectName: "doctorRefreshButton"
                    Accessible.name: "Refrescar estado del diagnóstico"
                    onClicked: {
                        if (root.doc && typeof root.doc.refresh !== "undefined")
                            root.doc.refresh()
                    }
                }
            }

            LoadingState {
                width: parent.width
                visible: root._state === "LOADING"
                text: "Cargando diagnóstico..."
            }

            DoctorRepairProgress {
                id: repairProgress
                width: parent.width
                doc: root.doc
                visible: root.doc && root.doc.status === "repairing"
                onCancelRequested: {
                    if (root.doc && typeof root.doc.cancelScan !== "undefined")
                        root.doc.cancelScan()
                }
            }

            DoctorIssueList {
                id: issueList
                width: parent.width
                doc: root.doc
                visible: root.doc && root.doc.status === "done" && root.doc.issues.length > 0
                onIssueSelected: function(id, data) {
                    issueDetail.showIssue(data)
                }
            }

            DoctorIssueDetail {
                id: issueDetail
                width: parent.width
                doc: root.doc
                onFixAccepted: function(id) {
                    if (root.doc && typeof root.doc.setIssueSelected !== "undefined")
                        root.doc.setIssueSelected(id, true)
                }
                onFixRejected: function(id) {
                    if (root.doc && typeof root.doc.setIssueSelected !== "undefined")
                        root.doc.setIssueSelected(id, false)
                }
            }

            DoctorDryRunPage {
                id: dryRunPage
                width: parent.width
                doc: root.doc
                visible: root.doc && root.doc.status === "done" && root.doc.issueCount > 0
                onConfirmRepair: {
                    if (root.doc && typeof root.doc.repairSelected !== "undefined")
                        root.doc.repairSelected()
                    dryRunPage.reset()
                }
                onCancelRepair: {
                    dryRunPage.reset()
                }
            }

            DoctorReportPage {
                id: reportPage
                width: parent.width
                doc: root.doc
                onExportReport: {
                    if (typeof notificationBridge !== "undefined" && notificationBridge)
                        notificationBridge.showMessage("Reporte exportado", "success")
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Solo lectura — sin reparación automática"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
