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
    x: (parent.width - width) / 2; y: (parent.height - height) / 3

    Column {
        spacing: MichiTheme.spacing.md; width: 360

        Text {
            text: "Exportar \"" + root.playlistName + "\" como M3U"
            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap; width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width
            TextField {
                id: pathInput; width: parent.width - 80
                placeholderText: "Destino del archivo .m3u"
                text: root._exportPath
            }
            MichiButton {
                text: "Examinar"; variant: "secondary"
                onClicked: saveDialog.open()
            }
        }

        Text {
            text: root._status; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize; visible: text !== ""
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

    onAccepted: {
        if (!root._exportPath || root.playlistId < 0) return
        root._exporting = true
        if (root.bridge && typeof root.bridge.exportM3U !== "undefined") {
            var result = root.bridge.exportM3U(root.playlistId, root._exportPath)
            if (result && result.ok) {
                root._status = "Exportadas " + (result.count || 0) + " canciones"
                root.exportCompleted(root._exportPath, result.count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al exportar"
            }
        }
        root._exporting = false
    }

    onRejected: root.exportCancelled()
}
