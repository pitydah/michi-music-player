import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"
import "library_doctor"

Item {
    id: root

    objectName: "libraryDoctor.page"
    focus: true
    Accessible.role: Accessible.Pane
    Accessible.name: "Diagnóstico de biblioteca"
    Accessible.description: "Analiza y detecta problemas en tu colección musical."

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
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        focus: true
        objectName: "libraryDoctor.flickable"

        Keys.onEscapePressed: function(event) {
            if (root.doc && typeof root.doc.cancelScan !== "undefined")
                root.doc.cancelScan()
            event.accepted = true
        }

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg
            objectName: "libraryDoctor.column"

            Text {
                id: titleText
                text: "Library Doctor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "libraryDoctor.title"
                Accessible.role: Accessible.Heading
                Accessible.name: "Library Doctor"
            }

            HeroMaterial {
                id: hero
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                objectName: "libraryDoctor.hero"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text { text: "Diagnóstico de biblioteca"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold; Accessible.role: Accessible.Heading; Accessible.name: "Diagnóstico de biblioteca" }
                    Text { text: "Analiza y detecta problemas en tu colección musical."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                }
            }

            Row {
                id: statusRow
                spacing: MichiTheme.spacing.md
                objectName: "libraryDoctor.statusRow"
                Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                StatusBadge {
                    id: statusBadge
                    text: root.doc ? root.doc.status : "no disponible"
                    kind: root.doc && root.doc.status === "done" ? "success" :
                          root.doc && root.doc.status === "scanning" ? "warning" :
                          root.doc && root.doc.status === "repairing" ? "error" :
                          root.doc && root.doc.status === "error" ? "error" : "info"
                    objectName: "libraryDoctor.statusBadge"
                }
                StatusBadge {
                    id: readonlyBadge
                    text: "Solo lectura"
                    kind: "info"
                    objectName: "libraryDoctor.readonlyBadge"
                }
            }

            Row {
                id: summaryRow
                spacing: MichiTheme.spacing.md
                objectName: "libraryDoctor.summaryRow"
                visible: root.doc && root.doc.status === "done"
                Text { text: "Revisados: " + (root.doc ? root.doc.totalChecked : 0); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; Accessible.name: "Revisados: " + (root.doc ? root.doc.totalChecked : 0) }
                Text { text: "Problemas: " + (root.doc ? root.doc.issueCount : 0); color: root.doc && root.doc.issueCount > 0 ? MichiTheme.colors.warning : MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.bodySize; Accessible.name: "Problemas: " + (root.doc ? root.doc.issueCount : 0) }
            }

            Row {
                id: detailRow
                spacing: MichiTheme.spacing.md
                objectName: "libraryDoctor.detailRow"
                visible: root.doc && root.doc.status === "done" && root.doc.issueCount > 0
                Text { text: "Metadata: " + (root.doc ? root.doc.missingMetadataCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                Text { text: "Archivos: " + (root.doc ? root.doc.missingFileCount : 0); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                Text { text: "OK: " + (root.doc ? root.doc.healthyCount : 0); color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.metaSize }
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm
                objectName: "libraryDoctor.actions"

                MichiButton {
                    id: scanBtn
                    text: root._state === "SCANNING" ? "Escaneando..." : "Escanear biblioteca"
                    variant: "primary"
                    objectName: "libraryDoctor.scanButton"
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
                    id: cancelBtn
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "libraryDoctor.cancelButton"
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
                    id: refreshBtn
                    text: "Refrescar"
                    variant: "ghost"
                    objectName: "libraryDoctor.refreshButton"
                    Accessible.name: "Refrescar estado del diagnóstico"
                    onClicked: {
                        if (root.doc && typeof root.doc.refresh !== "undefined")
                            root.doc.refresh()
                    }
                }
            }

            LoadingState {
                id: loadingState
                width: parent.width
                visible: root._state === "LOADING"
                text: "Cargando diagnóstico..."
                objectName: "libraryDoctor.loadingState"
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
