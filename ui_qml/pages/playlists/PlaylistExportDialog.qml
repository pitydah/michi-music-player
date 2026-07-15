import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int playlistId: -1
    property string playlistName: ""
    property string _exportPath: ""
    property bool _exporting: false
    property real _progress: 0
    property string _progressText: ""
    property bool _cancelled: false
    property string _status: ""

    signal exportCompleted(string path, int count)
    signal exportCancelled()

    title: "Exportar playlist"
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
<<<<<<< Updated upstream
    width: 400
    objectName: "playlistExportDialog"
=======
<<<<<<< HEAD
    objectName: "playlist.exportDialog"
    closePolicy: Dialog.CloseOnEscape

>>>>>>> Stashed changes
    Accessible.role: Accessible.Dialog
    Accessible.name: "Exportar playlist"
    closePolicy: Popup.CloseOnEscape

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: "Exportar \"" + root.playlistName + "\" como M3U"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Text {
            text: "Selecciona la ruta de destino para el archivo .m3u"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
            width: parent.width
            visible: !root._exporting
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            visible: !root._exporting

<<<<<<< Updated upstream
=======
            Text {
                text: "Exportar \"" + root.playlistName + "\""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
=======
    width: 400
    objectName: "playlistExportDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Exportar playlist"
    closePolicy: Popup.CloseOnEscape

    Column {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: "Exportar \"" + root.playlistName + "\" como M3U"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Text {
            text: "Selecciona la ruta de destino para el archivo .m3u"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
            width: parent.width
            visible: !root._exporting
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            visible: !root._exporting

>>>>>>> Stashed changes
            TextField {
                id: pathInput
                width: parent.width - 80
                placeholderText: "Destino del archivo .m3u"
                text: root._exportPath
                readOnly: true
                objectName: "exportPathInput"
                Accessible.name: "Ruta de destino"
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
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
=======
>>>>>>> Stashed changes
                text: "Examinar"
                variant: "secondary"
                objectName: "exportBrowseButton"
                Accessible.name: "Examinar destino"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: saveDialog.open()
<<<<<<< Updated upstream
            }

=======
>>>>>>> origin/michi-qml-functional-wave
            }

<<<<<<< HEAD
            Item { width: 1; height: 1; focus: true }
=======
>>>>>>> Stashed changes
        Rectangle {
            width: parent.width
            height: 4
            radius: MichiTheme.radiusPill
            color: MichiTheme.colors.controlTrack
            visible: root._exporting

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
            visible: root._exporting && root._progressText !== ""
        }

        Text {
            text: root._status
            color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                text: root._exporting ? "Exportando..." : "Exportar"
                variant: "primary"
                enabled: !root._exporting && root._exportPath !== ""
                objectName: "exportActionButton"
                Accessible.name: "Exportar playlist"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (!root._exportPath || root.playlistId < 0) return
                    root._exporting = true
                    root._cancelled = false
                    root._progress = 0.2
                    root._progressText = "Exportando..."
                    if (root.bridge && typeof root.bridge.exportM3U !== "undefined") {
                        root._progress = 0.6
                        root._progressText = "Escribiendo archivo..."
                        var result = root.bridge.exportM3U(root.playlistId, root._exportPath)
                        root._progress = 1.0
                        root._progressText = ""
                        if (result && result.ok) {
                            root._status = "Exportadas " + (result.count || 0) + " canciones"
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
                text: root._exporting ? "Cancelar" : "Cerrar"
                variant: "ghost"
                objectName: "exportCancelButton"
                Accessible.name: root._exporting ? "Cancelar exportación" : "Cerrar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    if (root._exporting) {
                        root._cancelled = true
                        root._progressText = "Cancelando..."
                        root._exporting = false
                        root._status = "Exportación cancelada"
                        root.exportCancelled()
                    } else {
                        root.close()
                    }
                }
            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }

    FileDialog {
        id: saveDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["M3U playlist (*.m3u)", "M3U8 playlist (*.m3u8)", "All files (*)"]
        defaultSuffix: ".m3u"
        objectName: "exportSaveDialog"
        Accessible.name: "Guardar archivo M3U"
        onAccepted: {
            root._exportPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._exportPath
        }
    }

<<<<<<< Updated upstream
    onOpened: {
        root._exportPath = ""
=======
<<<<<<< HEAD
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
=======
    onOpened: {
        root._exportPath = ""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        root._exporting = false
        root._cancelled = false
        root._progress = 0
        root._progressText = ""
        root._status = ""
        pathInput.text = ""
    }

<<<<<<< Updated upstream
    onClosed: {
=======
<<<<<<< HEAD
    onRejected: {
>>>>>>> Stashed changes
        if (root._exporting) {
            root._cancelled = true
            root._exporting = false
        }
<<<<<<< Updated upstream
=======
        root.exportCancelled()
=======
    onClosed: {
        if (root._exporting) {
            root._cancelled = true
            root._exporting = false
        }
>>>>>>> Stashed changes
    }

    QQC2.FocusTrap {
        active: root.opened
        focusItem: pathInput
    }

    Keys.onEscapePressed: {
        if (root._exporting) {
            root._cancelled = true
            root._exporting = false
            root._status = "Exportación cancelada"
            root.exportCancelled()
        } else {
            root.close()
        }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
}
