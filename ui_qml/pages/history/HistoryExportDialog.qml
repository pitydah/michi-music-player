import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property string _exportFormat: "json"
    property string _exportPath: ""
    property bool _exporting: false
    property real _progress: 0
    property string _progressText: ""
    property bool _cancelled: false
    property string _status: ""
    property int _estimatedSize: 0

    signal exportCompleted(string path, int count)
    signal exportCancelled()

    title: qsTr("Exportar historial")
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    width: 400
    objectName: "historyExportDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Exportar historial"
    closePolicy: Popup.NoAutoClose

    function _estimateSize() {
        if (!root.bridge || !root.bridge.historyQueryService ||
            typeof root.bridge.historyQueryService.estimateExportSize === "undefined") return
        var result = root.bridge.historyQueryService.estimateExportSize(root._exportFormat)
        root._estimatedSize = result && result.size_bytes ? result.size_bytes : 0
    }

    function _formatSize(bytes) {
        if (!bytes || bytes <= 0) return ""
        if (bytes < 1024) return bytes + " B"
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB"
        return (bytes / 1048576).toFixed(1) + " MB"
    }

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: qsTr("Exportar historial de reproducción")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            Text {
                text: qsTr("Formato:")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }
            ComboBox {
                Accessible.role: Accessible.ComboBox
                Accessible.name: "Formato de exportación"
                activeFocusOnTab: true
                focusPolicy: Qt.StrongFocus
                id: formatCombo
                model: ["json", "csv"]
                currentIndex: root._exportFormat === "csv" ? 1 : 0
                onCurrentTextChanged: {
                    root._exportFormat = currentText
                    root._estimateSize()
                }
            }
        }

        Text {
            text: qsTr("Ruta de destino:")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            visible: !root._exporting
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            visible: !root._exporting

            TextField {
                focusPolicy: Qt.StrongFocus
                Accessible.name: "Ruta de destino"
                id: pathInput

                width: parent.width - 80
                placeholderText: qsTr("Selecciona ruta de destino...")
                readOnly: true
                text: root._exportPath
            }
            MichiButton {
                text: qsTr("Examinar")
                variant: "secondary"
                onClicked: saveDialog.open()
            }
        }

        Text {
            text: root._estimatedSize > 0 ? "Tamaño estimado: qsTr(" + _formatSize(root._estimatedSize) : ")"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== "" && !root._exporting
        }

        Rectangle {
    focus: true
            width: parent.width
            height: 4
            radius: MichiTheme.radius.pill
            color: MichiTheme.colors.controlTrack
            visible: root._exporting

            Rectangle {
                width: parent.width * root._progress
                height: parent.height
                radius: MichiTheme.radius.pill
                color: MichiTheme.colors.accentBlue

                Behavior on width { NumberAnimation { duration: 200 } }
            }
        }

        Text {
            text: root._progressText
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._exporting && root._progressText !== ""
        }

        Text {
            text: root._status
            color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
            wrapMode: Text.WordWrap
            width: parent.width
                Accessible.role: Accessible.Button

        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                id: exportActionBtn
                text: root._exporting ? "Exportando..." : root._exportPath ? "Exportar" : qsTr("Seleccionar destino")
                variant: "primary"
                enabled: !root._exporting && (root._exportPath !== "" || !root._exportPath)
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (!root._exportPath) {
                        saveDialog.open()
                        return
                    }
                    root._exporting = true
                    root._cancelled = false
                    root._progress = 0
                    root._progressText = "Iniciando exportación..."
                    root._status = ""
                    if (root.bridge && typeof root.bridge.exportHistory !== "undefined") {
                        root._progress = 0.3
                        root._progressText = "Recopilando datos..."
                        var result = root.bridge.exportHistory(root._exportPath, root._exportFormat)
                        root._progress = 1.0
                        root._progressText = ""
                        if (result && result.ok) {
                            root._status = "Exportadas " + (result.count || 0) + " entradas"
                            root.exportCompleted(root._exportPath, result.count || 0)
                        } else {
                            root._status = result && result.error ? "Error: " + result.error : "Error al exportar"
                        }
                    } else {
                        root._status = "Error: servicio no disponible"
                    }
                    root._exporting = false
                }
            }

            MichiButton {
                text: root._exporting ? "Cancelar" : qsTr("Cerrar")
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root._exporting) {
                        root._cancelled = true
                        root._progressText = "Cancelando..."
                        if (root.bridge && typeof root.bridge.cancelExport !== "undefined")
                            root.bridge.cancelExport(root._exportPath)
                        root._exporting = false
                        root._status = "Exportación cancelada"
                        root.exportCancelled()
                    } else {
                        root.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: saveDialog
        fileMode: FileDialog.SaveFile
        nameFilters: root._exportFormat === "json" ? ["JSON files (*.json)", "All files (*)"]
                                                    : ["CSV files (*.csv)", "All files (*)"]
        defaultSuffix: root._exportFormat === "json" ? ".json" : ".csv"
        onAccepted: {
            root._exportPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._exportPath
            root._estimateSize()
        }
        onRejected: { }
    }

    onOpened: {
        root._exportPath = ""
        root._exporting = false
        root._cancelled = false
        root._progress = 0
        root._progressText = ""
        root._status = ""
        root._estimateSize()
        pathInput.text = ""
    }

    onClosed: {
        if (root._exporting) {
            root._cancelled = true
            if (root.bridge && typeof root.bridge.cancelExport !== "undefined")
                root.bridge.cancelExport(root._exportPath)
            root._exporting = false
        }
    }

    Item {
        focus: root.opened
    }

    Keys.onEscapePressed: {
        if (root._exporting) {
            root._cancelled = true
            if (root.bridge && typeof root.bridge.cancelExport !== "undefined")
                root.bridge.cancelExport(root._exportPath)
            root._exporting = false
            root._status = "Exportación cancelada"
            root.exportCancelled()
        } else {
            root.close()
        }
    }
}
