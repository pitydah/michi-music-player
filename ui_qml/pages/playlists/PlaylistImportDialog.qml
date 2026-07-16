import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property string _importPath: ""
    property var _preview: null
    property bool _importing: false
    property real _progress: 0
    property string _progressText: ""
    property bool _cancelled: false
    property string _status: ""
    property int _totalEntries: 0
    property int _validEntries: 0
    property int _missingEntries: 0

    signal importCompleted(string name, int count)
    signal importCancelled()

    title: "Importar playlist"
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    width: 420
    objectName: "playlistImportDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Importar playlist"
    closePolicy: Popup.NoAutoClose

    function resetDialog() {
        root._importPath = ""
        root._preview = null
        root._importing = false
        root._progress = 0
        root._progressText = ""
        root._cancelled = false
        root._status = ""
        root._totalEntries = 0
        root._validEntries = 0
        root._missingEntries = 0
        pathInput.text = ""
    }

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 380

        Text {
            text: "Selecciona un archivo de lista de reproducción"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Text {
            text: "Formatos compatibles: M3U, M3U8, PLS, XSPF"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            visible: !root._importing

            TextField {
                id: pathInput
                width: parent.width - 80
                placeholderText: "Ruta del archivo (.m3u, .pls, .xspf)"
                readOnly: true
                text: root._importPath
                objectName: "importPathInput"
                Accessible.name: "Ruta del archivo"
            }
            MichiButton {
                text: "Examinar"
                variant: "secondary"
                objectName: "importBrowseButton"
                Accessible.name: "Examinar archivo"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: fileDialog.open()
            }
        }

        Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Playlist Import"
    objectName: "playlistImportDialog"
    focus: true
            width: parent.width
            height: 4
            radius: MichiTheme.radiusPill
            color: MichiTheme.colors.controlTrack
            visible: root._importing

            Rectangle {
                width: parent.width * root._progress
                height: parent.height
                radius: MichiTheme.radiusPill
                color: MichiTheme.colors.accentBlue
                Behavior on width { NumberAnimation { duration: 200 } }
            }
        }

        Text {
            text: root._progressText
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: root._importing && root._progressText !== ""
        }

        Column {
            spacing: MichiTheme.spacing.xs
            width: parent.width
            visible: root._preview !== null && !root._importing

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Text {
                text: "Vista previa:"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            Text {
                text: "Total entradas: " + root._totalEntries
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                Accessible.name: "Total entradas: " + root._totalEntries
            }
            Text {
                text: "Válidas: " + root._validEntries
                color: MichiTheme.colors.success
                font.pixelSize: MichiTheme.typography.metaSize
                Accessible.name: "Entradas válidas: " + root._validEntries
            }
            Text {
                text: "Faltantes: " + root._missingEntries
                color: root._missingEntries > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                Accessible.name: "Entradas faltantes: " + root._missingEntries
            }

            Repeater {
                model: root._preview && root._preview.entries ? root._preview.entries.slice(0, 5) : []
                delegate: Text {
                    text: (index + 1) + ". " + (modelData.title || modelData.path || "")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            Text {
                text: (root._preview && root._preview.entries && root._preview.entries.length > 5)
                      ? "... y " + (root._preview.entries.length - 5) + " más" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: text !== ""
            }
        }

        Text {
            text: root._status
            color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                text: root._importing ? "Importando..." : "Importar"
                variant: "primary"
                enabled: !root._importing && root._importPath !== "" && root._validEntries > 0
                objectName: "importConfirmButton"
                Accessible.name: "Confirmar importación"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (!root._importPath) return
                    root._importing = true
                    root._cancelled = false
                    root._progress = 0.1
                    root._progressText = "Importando..."
                    if (root.bridge && typeof root.bridge.confirmPlaylistImport !== "undefined") {
                        root._progress = 0.5
                        root._progressText = "Procesando canciones..."
                        var result = root.bridge.confirmPlaylistImport(root._importPath)
                        root._progress = 1.0
                        root._progressText = ""
                        if (result && result.ok) {
                            root._status = "Importada \"" + (result.name || "Importada") +
                                          "\" (" + (result.count || 0) + " canciones)"
                            root.importCompleted(result.name || "Importada", result.count || 0)
                        } else {
                            root._status = result && result.error ? "Error: " + result.error : "Error al importar"
                        }
                    } else {
                        root._status = "Error: servicio no disponible"
                    }
                    root._importing = false
                }
            }

            MichiButton {
                text: root._importing ? "Cancelar" : "Cerrar"
                variant: "ghost"
                objectName: "importCancelButton"
                Accessible.name: root._importing ? "Cancelar importación" : "Cerrar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root._importing) {
                        root._cancelled = true
                        root._progressText = "Cancelando..."
                        if (root.bridge && typeof root.bridge.cancelPlaylistImport !== "undefined")
                            root.bridge.cancelPlaylistImport(root._importPath)
                        root._importing = false
                        root._status = "Importación cancelada"
                        root.importCancelled()
                    } else {
                        root.close()
                    }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        nameFilters: [
            "Playlist files (*.m3u *.m3u8 *.pls *.xspf)",
            "M3U files (*.m3u *.m3u8)",
            "PLS files (*.pls)",
            "XSPF files (*.xspf)",
            "All files (*)"
        ]
        objectName: "importFileDialog"
        Accessible.name: "Seleccionar archivo de playlist"
        onAccepted: {
            root._importPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._importPath
            if (root.bridge && typeof root.bridge.previewPlaylistImport !== "undefined") {
                root._preview = root.bridge.previewPlaylistImport(root._importPath)
                if (root._preview && root._preview.ok) {
                    root._totalEntries = root._preview.total_entries || 0
                    root._validEntries = root._preview.valid_entries || 0
                    root._missingEntries = root._preview.missing_entries || 0
                    root._status = "Vista previa generada. Entradas: " + root._totalEntries +
                                   " | Válidas: " + root._validEntries +
                                   " | Faltantes: " + root._missingEntries
                } else {
                    root._status = root._preview && root._preview.error
                                   ? "Error: " + root._preview.error : "Error al previsualizar"
                }
            } else {
                root._status = "Vista previa no disponible. Selecciona un archivo para importar."
            }
        }
    }

    onOpened: root.reset()
    onClosed: {
        if (root._importing) {
            root._cancelled = true
            if (root.bridge && typeof root.bridge.cancelPlaylistImport !== "undefined")
                root.bridge.cancelPlaylistImport(root._importPath)
            root._importing = false
        }
    }

    Item {
        focus: root.opened
    }

    Keys.onEscapePressed: {
        if (root._importing) {
            root._cancelled = true
            if (root.bridge && typeof root.bridge.cancelPlaylistImport !== "undefined")
                root.bridge.cancelPlaylistImport(root._importPath)
            root._importing = false
            root._status = "Importación cancelada"
            root.importCancelled()
        } else {
            root.close()
        }
    }
}
