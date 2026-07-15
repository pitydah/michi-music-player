import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int _exportJobId: 0
    property bool _exporting: false
    property real _progress: 0
    property string _status: ""
    property string _exportPath: ""
    property string _exportFormat: "json"

    signal exportCompleted(string path, int count)
    signal exportCancelled()

    title: "Exportar historial"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    objectName: "history.exportDialog"
    closePolicy: Dialog.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: "Exportar historial"
    Accessible.description: "Diálogo para exportar el historial de reproducción"

    Keys.onEscapePressed: {
        if (!root._exporting) root.reject()
    }

    onOpened: {
        root._exportPath = ""
        root._exportFormat = "json"
        root._exporting = false
        root._progress = 0
        root._status = ""
        formatCombo.currentIndex = 0
        pathInput.forceActiveFocus()
    }

    onAccepted: {
        if (!root._exportPath || root._exporting) return
        root._exporting = true
        root._progress = 0
        root._status = "Exportando..."
        root._exportJobId = Qt.createQmlObject("import QtQuick; Timer {}", root).setInterval
        if (root.bridge && typeof root.bridge.exportHistory !== "undefined") {
            var result = root.bridge.exportHistory(root._exportPath, root._exportFormat)
            if (result && result.ok) {
                root._progress = 100
                root._status = "Exportación completada: " + (result.count || 0) + " registros"
                root.exportCompleted(root._exportPath, result.count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al exportar"
                root._progress = 0
            }
        } else {
            root._status = "Error: bridge no disponible"
        }
        root._exporting = false
    }

    onRejected: {
        if (root._exporting) {
            if (root.bridge && typeof root.bridge.cancelExport !== "undefined") {
                root.bridge.cancelExport(String(root._exportJobId), root._exportPath)
            }
            root._status = "Exportación cancelada"
            root._exporting = false
            root.exportCancelled()
        }
    }

    FocusScope {
        id: focusTrap
        anchors.fill: parent
        activeFocusOnTab: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md
            width: 360

            Text {
                text: "Exportar registros del historial"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: "Formato:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }

                ComboBox {
                    id: formatCombo
                    width: 120
                    model: ["json", "csv"]
                    onCurrentTextChanged: root._exportFormat = currentText
                    objectName: "history.exportDialog.formatCombo"
                    Accessible.name: "Formato de exportación"
                    KeyNavigation.tab: pathInput
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                TextField {
                    id: pathInput
                    width: parent.width - 80
                    placeholderText: "Ruta del archivo de exportación"
                    text: root._exportPath
                    onTextChanged: root._exportPath = text
                    objectName: "history.exportDialog.pathInput"
                    Accessible.name: "Ruta de exportación"
                    KeyNavigation.tab: browseBtn
                    KeyNavigation.backtab: formatCombo
                }

                MichiButton {
                    id: browseBtn
                    text: "Examinar"
                    variant: "secondary"
                    onClicked: saveDialog.open()
                    objectName: "history.exportDialog.browseBtn"
                    Accessible.name: "Examinar ruta de exportación"
                    KeyNavigation.tab: progressBar
                    KeyNavigation.backtab: pathInput
                }
            }

            MichiProgressBar {
                id: progressBar
                width: parent.width
                value: root._progress
                from: 0; to: 100
                indeterminate: root._exporting && root._progress <= 0
                accessibleName: "Progreso de exportación"
                accessibleDescription: root._status
                objectName: "history.exportDialog.progressBar"
                KeyNavigation.tab: cancelExportBtn
                KeyNavigation.backtab: browseBtn
            }

            Text {
                text: root._status
                color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                wrapMode: Text.WordWrap
                width: parent.width
                Accessible.role: Accessible.StatusBar
                Accessible.name: root._status
            }

            MichiButton {
                id: cancelExportBtn
                text: "Cancelar exportación"
                variant: "danger"
                visible: root._exporting
                onClicked: {
                    if (root.bridge && typeof root.bridge.cancelExport !== "undefined") {
                        root.bridge.cancelExport(String(root._exportJobId), root._exportPath)
                    }
                    root._exporting = false
                    root._status = "Exportación cancelada"
                    root.exportCancelled()
                }
                objectName: "history.exportDialog.cancelBtn"
                Accessible.name: "Cancelar exportación"
                KeyNavigation.backtab: progressBar
            }

            Item { width: 1; height: 1; focus: true }
        }
    }

    FileDialog {
        id: saveDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON (*.json)", "CSV (*.csv)", "All files (*)"]
        defaultSuffix: root._exportFormat === "json" ? ".json" : ".csv"
        onAccepted: {
            root._exportPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._exportPath
        }
    }
}
