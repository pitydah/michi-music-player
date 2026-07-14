import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int retentionDays: 365
    property bool _applying: false
    property string _status: ""

    signal retentionApplied(int deletedCount)
    signal retentionCancelled()

    title: "Política de retención"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2; y: (parent.height - height) / 3

    Column {
        spacing: MichiTheme.spacing.md; width: 320

        Text {
            text: "Configurar retención del historial de reproducción"
            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap; width: parent.width
        }

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width
            Text {
                text: "Mantener registros de los últimos:"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
            }
            SpinBox {
                id: daysSpin; from: 7; to: 3650; value: root.retentionDays
                onValueChanged: root.retentionDays = value
            }
            Text {
                text: "días"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: "Los registros anteriores a " + root.retentionDays + " días serán eliminados permanentemente."
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap; width: parent.width
        }

        Text {
            text: root._status; color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize; visible: text !== ""
        }
    }

    onAccepted: {
        root._applying = true
        if (root.bridge && root.bridge.historyQueryService &&
            typeof root.bridge.historyQueryService.applyRetention !== "undefined") {
            var result = root.bridge.historyQueryService.applyRetention(root.retentionDays)
            if (result && result.ok) {
                root._status = "Eliminados " + (result.deleted_count || 0) + " registros"
                root.retentionApplied(result.deleted_count || 0)
            } else {
                root._status = "Error al aplicar retención"
            }
        }
        root._applying = false
    }

    onRejected: root.retentionCancelled()
}
