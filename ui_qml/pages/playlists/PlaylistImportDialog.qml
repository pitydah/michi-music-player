import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property string _importPath: ""
    property var _preview: null
    property bool _importing: false
    property string _status: ""

    signal importCompleted(string name, int count)
    signal importCancelled()

    title: "Importar playlist"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2; y: (parent.height - height) / 3

    Column {
        spacing: MichiTheme.spacing.md; width: 360

        Text {
            text: "Selecciona un archivo M3U/M3U8 para importar"
            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap; width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width
            TextField {
                id: pathInput; width: parent.width - 80
                placeholderText: "Ruta del archivo .m3u"; readOnly: true
                text: root._importPath
            }
            MichiButton {
                text: "Examinar"; variant: "secondary"
                onClicked: fileDialog.open()
            }
        }

        Text {
            text: root._status; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize; visible: text !== ""
            wrapMode: Text.WordWrap; width: parent.width
        }
    }

    FileDialog {
        id: fileDialog
        nameFilters: ["Playlist files (*.m3u *.m3u8)", "All files (*)"]
        onAccepted: {
            root._importPath = selectedFile.toString().replace("file://", "")
            if (root.bridge && typeof root.bridge.previewPlaylistImport !== "undefined") {
                root._preview = root.bridge.previewPlaylistImport(root._importPath)
                if (root._preview && root._preview.ok) {
                    root._status = "Encontrados: " + root._preview.total_entries +
                                  " | Válidos: " + root._preview.valid_entries +
                                  " | Faltantes: " + root._preview.missing_entries
                } else {
                    root._status = root._preview && root._preview.error ? "Error: " + root._preview.error : "Error al previsualizar"
                }
            }
        }
    }

    onAccepted: {
        if (!root._importPath) return
        root._importing = true
        if (root.bridge && typeof root.bridge.confirmPlaylistImport !== "undefined") {
            var result = root.bridge.confirmPlaylistImport(root._importPath)
            if (result && result.ok) {
                root.importCompleted(result.name || "Importada", result.count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al importar"
            }
        }
        root._importing = false
    }

    onRejected: root.importCancelled()
}
