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

            TextField {
                Accessible.name: "Nombre del archivo"
                activeFocusOnTab: true
                focusPolicy: Qt.StrongFocus
                id: pathInput
                width: parent.width - 80
                placeholderText: "Destino del archivo .m3u"
                text: root._exportPath
                Accessible.role: Accessible.Button

                readOnly: true
            }
            MichiButton {
                text: "Examinar"
                variant: "secondary"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: saveDialog.open()
            }
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
        }

        Row {
            spacing: MichiTheme.spacing.sm
                Accessible.role: Accessible.Button

            width: parent.width
            layoutDirection: Qt.RightToLeft

            MichiButton {
                text: root._exporting ? "Exportando..." : "Exportar"
                variant: "primary"
                enabled: !root._exporting && root._exportPath !== ""
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
        }
    }

    FileDialog {
        id: saveDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["M3U playlist (*.m3u)", "All files (*)"]
        defaultSuffix: ".m3u"
        onAccepted: {
            root._exportPath = selectedFile.toString().replace("file://", "")
            pathInput.text = root._exportPath
        }
    }

    onOpened: {
        root._exportPath = ""
        root._exporting = false
        root._cancelled = false
        root._progress = 0
        root._progressText = ""
        root._status = ""
        pathInput.text = ""
    }

    onClosed: {
        if (root._exporting) {
            root._cancelled = true
            root._exporting = false
        }
    }

    Item {
        focus: root.opened
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
    }
}
