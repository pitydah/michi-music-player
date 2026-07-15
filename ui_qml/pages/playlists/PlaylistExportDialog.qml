import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int playlistId: -1
    property string playlistName: ""
    property string _exportPath: ""
    property bool _exporting: false
    property string _status: ""

    signal exportCompleted(string path, int count)
    signal exportCancelled()

    title: "Exportar playlist"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    objectName: "playlist.exportDialog"
    closePolicy: Dialog.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: "Exportar playlist"
    Accessible.description: "Diálogo para exportar la playlist a un archivo"

    Keys.onEscapePressed: {
        if (!root._exporting) root.reject()
    }

    onOpened: {
        root._exportPath = ""
        root._exporting = false
        root._status = ""
    }

    FocusScope {
        id: focusTrap
        anchors.fill: parent
        activeFocusOnTab: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md
            width: 380

            Text {
                text: "Exportar \"" + root.playlistName + "\""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Text {
                text: "Formato: M3U"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                TextField {
                    id: pathInput
                    width: parent.width - 80
                    placeholderText: "Destino del archivo .m3u"
                    text: root._exportPath
                    onTextChanged: root._exportPath = text
                    objectName: "playlist.exportDialog.pathInput"
                    Accessible.name: "Ruta de exportación"
                    KeyNavigation.tab: browseBtn
                }

                MichiButton {
                    id: browseBtn
                    text: "Examinar"
                    variant: "secondary"
                    onClicked: saveDialog.open()
                    objectName: "playlist.exportDialog.browseBtn"
                    Accessible.name: "Examinar ruta de exportación"
                    KeyNavigation.tab: progressBar
                    KeyNavigation.backtab: pathInput
                }
            }

            MichiProgressBar {
                id: progressBar
                width: parent.width
                value: root._exporting ? 100 : 0
                indeterminate: root._exporting
                visible: root._exporting
                accessibleName: "Progreso de exportación"
                objectName: "playlist.exportDialog.progressBar"
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
                    root._exporting = false
                    root._status = "Exportación cancelada"
                    root.exportCancelled()
                }
                objectName: "playlist.exportDialog.cancelBtn"
                Accessible.name: "Cancelar exportación"
                KeyNavigation.backtab: progressBar
            }

            Item { width: 1; height: 1; focus: true }
        }
    }

    FileDialog {
        id: saveDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["M3U playlist (*.m3u)", "M3U8 playlist (*.m3u8)", "All files (*)"]
        defaultSuffix: ".m3u"
        onAccepted: {
            root._exportPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._exportPath
        }
    }

    onAccepted: {
        if (!root._exportPath || root.playlistId < 0) return
        root._exporting = true
        root._status = "Exportando..."
        if (root.bridge && typeof root.bridge.exportM3U !== "undefined") {
            var result = root.bridge.exportM3U(root.playlistId, root._exportPath)
            if (result && result.ok) {
                root._status = "Exportadas " + (result.count || 0) + " canciones"
                root.exportCompleted(root._exportPath, result.count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al exportar"
            }
        } else {
            root._status = "Bridge no disponible"
        }
        root._exporting = false
    }

    onRejected: {
        if (root._exporting) {
            root._exporting = false
        }
        root.exportCancelled()
    }
}
