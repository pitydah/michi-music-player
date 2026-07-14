import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property int sourceId: 0
    property var bridge: null

    title: "Editar fuente"
    width: 400
    height: 300
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.md

        Text {
            text: "Nombre"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }

        TextField {
            id: nameField
            Layout.fillWidth: true
            placeholderText: "Nombre de la fuente"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
        }

        Text {
            text: "Ruta"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.sm

            TextField {
                id: pathField
                Layout.fillWidth: true
                placeholderText: "/ruta/a/música"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }

            MichiButton { text: "Buscar"; variant: "ghost"; onClicked: folderDialog.open() }
        }

        FolderDialog {
            id: folderDialog
            onAccepted: { pathField.text = selectedFolder.toLocalFile() }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            CheckBox { id: watchCheck; text: "Watch mode (vigilancia automática)" }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            Text { text: "Prioridad"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            SpinBox { id: prioritySpin; from: 0; to: 100; value: 50 }
        }
    }

    onAccepted: {
        if (root.bridge && root.bridge.updateSource) {
            root.bridge.updateSource(root.sourceId, {
                name: nameField.text,
                path: pathField.text,
                watch_mode: watchCheck.checked,
                priority: prioritySpin.value
            })
        }
    }
}
