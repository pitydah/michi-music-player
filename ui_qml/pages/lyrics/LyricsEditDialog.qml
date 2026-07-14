import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Dialog {
    id: root

    property var lyricsBridge: null

    title: "Editar letra"
    modal: true
    standardButtons: Dialog.Close
    width: Math.min(parent.width * 0.85, 600)
    height: Math.min(parent.height * 0.7, 500)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 4

    padding: MichiTheme.spacing.lg

    Column {
        spacing: MichiTheme.spacing.md
        width: parent.width
        height: parent.height

        Text {
            text: "Edita la letra manualmente. Los cambios se guardarán localmente."
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            wrapMode: Text.WordWrap
            width: parent.width
        }

        ScrollView {
            width: parent.width
            height: parent.height - 100

            TextArea {
                id: editor
                width: parent.width
                text: root.lyricsBridge ? root.lyricsBridge.lyrics : ""
                placeholderText: "Escribe la letra aquí..."
                font.pixelSize: MichiTheme.typography.bodySize
                color: MichiTheme.colors.textPrimary
                wrapMode: Text.WordWrap
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                text: "Cancelar"
                flat: true
                onClicked: root.close()
            }

            Button {
                text: "Guardar"
                enabled: editor.text.trim() !== ""
                onClicked: {
                    if (root.lyricsBridge && typeof root.lyricsBridge.saveLocalLyrics === "function") {
                        var r = root.lyricsBridge.saveLocalLyrics(editor.text)
                        if (r.ok) root.close()
                    } else {
                        root.close()
                    }
                }
            }
        }
    }
}
