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
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    objectName: "playlist.importDialog"
    closePolicy: Dialog.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: "Importar playlist"
    Accessible.description: "Diálogo para importar una playlist desde un archivo"

    Keys.onEscapePressed: {
        if (!root._importing) root.reject()
    }

    onOpened: {
        root._importPath = ""
        root._preview = null
        root._importing = false
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
                text: "Selecciona un archivo de playlist para importar"
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

                TextField {
                    id: pathInput
                    width: parent.width - 80
                    placeholderText: "Ruta del archivo de playlist"
                    readOnly: true
                    text: root._importPath
                    objectName: "playlist.importDialog.pathInput"
                    Accessible.name: "Ruta del archivo a importar"
                    KeyNavigation.tab: browseBtn
                }

                MichiButton {
                    id: browseBtn
                    text: "Examinar"
                    variant: "secondary"
                    onClicked: fileDialog.open()
                    objectName: "playlist.importDialog.browseBtn"
                    Accessible.name: "Examinar archivo de playlist"
                    KeyNavigation.tab: progressBar
                    KeyNavigation.backtab: pathInput
                }
            }

            Rectangle {
                width: parent.width
                height: 80
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surface
                visible: root._preview !== null && root._preview.ok

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Vista previa de importación"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                    Text {
                        text: "Total: " + (root._preview.total_entries || 0) + " | Válidos: " + (root._preview.valid_entries || 0)
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                    Text {
                        text: "Faltantes: " + (root._preview.missing_entries || 0)
                        color: (root._preview.missing_entries || 0) > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
            }

            MichiProgressBar {
                id: progressBar
                width: parent.width
                value: root._importing ? 100 : 0
                indeterminate: root._importing
                visible: root._importing
                accessibleName: "Progreso de importación"
                objectName: "playlist.importDialog.progressBar"
                KeyNavigation.tab: cancelImportBtn
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
                id: cancelImportBtn
                text: "Cancelar importación"
                variant: "danger"
                visible: root._importing
                onClicked: {
                    if (root.bridge && typeof root.bridge.cancelPlaylistImport !== "undefined") {
                        root.bridge.cancelPlaylistImport(root._importPath)
                    }
                    root._importing = false
                    root._status = "Importación cancelada"
                    root.importCancelled()
                }
                objectName: "playlist.importDialog.cancelBtn"
                Accessible.name: "Cancelar importación"
                KeyNavigation.backtab: progressBar
            }

            Item { width: 1; height: 1; focus: true }
        }
    }

    FileDialog {
        id: fileDialog
        nameFilters: [
            "Playlist files (*.m3u *.m3u8 *.pls *.xspf)",
            "M3U playlists (*.m3u *.m3u8)",
            "PLS playlists (*.pls)",
            "XSPF playlists (*.xspf)",
            "All files (*)"
        ]
        onAccepted: {
            root._importPath = selectedFile.toString().replace("file://", "")
            if (root.bridge && typeof root.bridge.previewPlaylistImport !== "undefined") {
                root._preview = root.bridge.previewPlaylistImport(root._importPath)
                if (root._preview && root._preview.ok) {
                    root._status = "Vista previa cargada"
                } else {
                    root._status = root._preview && root._preview.error ? "Error: " + root._preview.error : "Error al previsualizar"
                }
            }
        }
    }

    onAccepted: {
        if (!root._importPath) return
        root._importing = true
        root._status = "Importando..."
        if (root.bridge && typeof root.bridge.confirmPlaylistImport !== "undefined") {
            var result = root.bridge.confirmPlaylistImport(root._importPath)
            if (result && result.ok) {
                root._status = "Importada: " + (result.name || "desconocida") + " (" + (result.count || 0) + " canciones)"
                root.importCompleted(result.name || "Importada", result.count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al importar"
            }
        } else {
            root._status = "Bridge no disponible"
        }
        root._importing = false
    }

    onRejected: {
        if (root._importing) {
            if (root.bridge && typeof root.bridge.cancelPlaylistImport !== "undefined") {
                root.bridge.cancelPlaylistImport(root._importPath)
            }
            root._importing = false
        }
        root.importCancelled()
    }
}
