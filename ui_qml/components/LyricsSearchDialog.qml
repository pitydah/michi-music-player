import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Dialog {
    id: root
    closePolicy: Popup.CloseOnEscape

    property var lyricsBridge: null

    title: "Buscar letra"
    modal: true
    standardButtons: Dialog.Close
    width: Math.min(parent.width * 0.8, 500)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3

    padding: MichiTheme.spacing.lg

    Column {
            Accessible.role: Accessible.EditableText

            Accessible.name: "Campo de texto"

            activeFocusOnTab: true

        spacing: MichiTheme.spacing.md
        width: parent.width

        TextField {
            focusPolicy: Qt.StrongFocus
            id: queryField
            width: parent.width
            placeholderText: "Artista — Canción"
            onAccepted: {
                if (text.trim()) {
                    root.lyricsBridge.searchManual(text.trim())
                    root.close()
                }
            }
                Accessible.role: Accessible.Button

                Accessible.name: "Button"

                activeFocusOnTab: true

        }

        Row {
                Accessible.role: Accessible.Button

                Accessible.name: "Button"

                activeFocusOnTab: true

            spacing: MichiTheme.spacing.sm
            anchors.horizontalCenter: parent.horizontalCenter

            Button {
                text: "Cancelar"
                flat: true
                onClicked: root.close()
            }

            Button {
                text: "Buscar"
                enabled: queryField.text.trim() !== ""
                onClicked: {
                    root.lyricsBridge.searchManual(queryField.text.trim())
                    root.close()
                }
            }
        }

        Text {
            text: "Usa el formato: Artista — Canción"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
