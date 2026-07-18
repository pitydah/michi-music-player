import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor"
    objectName: "libraryDoctorPage"
    focus: true
    id: root

    property var doc: typeof libraryDoctorBridge !== "undefined" ? libraryDoctorBridge : null
    property int pageState: root.doc ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    Component.onCompleted: {
        if (root.doc && typeof root.doc.refresh !== "undefined")
            root.doc.refresh()
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando Library Doctor" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: "Library Doctor no disponible" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin datos de biblioteca" }
    }

    Flickable {
        visible: root.pageState === root.stateReady
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
                text: "Library Doctor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            LibraryDoctorOverview {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorScanPage {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorIssueList {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorFixPreview {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorProgress {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorReport {
                width: parent.width
                doc: root.doc
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: "Exportar reporte"
                    variant: "ghost"
                    onClicked: exportDialog.open()
                }

                FileDialog {
                    id: exportDialog
                    title: "Exportar reporte"
                    fileMode: FileDialog.SaveFile
                    nameFilters: ["JSON (*.json)", "CSV (*.csv)"]
                    defaultSuffix: "json"
                    currentFile: "library_doctor_report.json"
                    onAccepted: {
                        var filePath = exportDialog.selectedFile.toString()
                        if (filePath.startsWith("file://"))
                            filePath = filePath.slice(7)
                        var fmt = "json"
                        if (filePath.endsWith(".csv"))
                            fmt = "csv"
                        if (root.doc && typeof root.doc.exportReport !== "undefined") {
                            var result = root.doc.exportReport(filePath, fmt)
                            if (typeof notificationBridge !== "undefined" && notificationBridge) {
                                if (result.ok)
                                    notificationBridge.showMessage("Reporte exportado a " + filePath, "success")
                                else
                                    notificationBridge.showMessage(result.message || "Error al exportar", "error")
                            }
                        }
                    }
                }
                MichiButton {
                    text: "Refrescar biblioteca"
                    variant: "ghost"
                    onClicked: {
                        if (root.doc && typeof root.doc.refresh !== "undefined")
                            root.doc.refresh()
                    }
                }
            }
        }
    }
}
