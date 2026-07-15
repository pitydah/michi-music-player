import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int retentionDays: 365
    property int maxEntries: 10000
    property bool autoClean: false
    property bool _applying: false
    property string _status: ""

    signal retentionApplied(int deletedCount)
    signal retentionCancelled()

    title: "Política de retención"
    standardButtons: Dialog.Ok | Dialog.Cancel
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    objectName: "history.retentionDialog"
    closePolicy: Dialog.CloseOnEscape

    Accessible.role: Accessible.Dialog
    Accessible.name: "Configurar retención de historial"
    Accessible.description: "Diálogo para configurar la política de retención del historial"

    Keys.onEscapePressed: {
        if (!root._applying) root.reject()
    }

    onOpened: {
        root._status = ""
        root._applying = false
        daysSpin.forceActiveFocus()
    }

    FocusScope {
        id: focusTrap
        anchors.fill: parent
        activeFocusOnTab: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md
            width: 340

            Text {
                text: "Configurar retención del historial de reproducción"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: "Mantener registros de los últimos:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }

                SpinBox {
                    id: daysSpin
                    from: 7
                    to: 3650
                    value: root.retentionDays
                    onValueChanged: root.retentionDays = value
                    objectName: "history.retentionDialog.daysSpin"
                    Accessible.name: "Días de retención"
                    KeyNavigation.tab: maxEntriesSpin
                }

                Text {
                    text: "días"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: "Máximo de entradas:"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }

                SpinBox {
                    id: maxEntriesSpin
                    from: 100
                    to: 100000
                    stepSize: 100
                    value: root.maxEntries
                    onValueChanged: root.maxEntries = value
                    objectName: "history.retentionDialog.maxEntriesSpin"
                    Accessible.name: "Máximo de entradas en el historial"
                    KeyNavigation.tab: autoCleanCheck
                    KeyNavigation.backtab: daysSpin
                }
            }

            CheckBox {
                id: autoCleanCheck
                text: "Limpiar automáticamente al iniciar"
                checked: root.autoClean
                onCheckedChanged: root.autoClean = checked
                objectName: "history.retentionDialog.autoClean"
                Accessible.name: "Limpiar automáticamente al iniciar"
                KeyNavigation.tab: okBtn
                KeyNavigation.backtab: maxEntriesSpin
            }

            Text {
                text: "Los registros anteriores a " + root.retentionDays + " días serán eliminados permanentemente."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Text {
                text: root._status
                color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                Accessible.role: Accessible.StatusBar
                Accessible.name: root._status
            }

            Item { width: 1; height: 1; focus: true }
        }
    }

    onAccepted: {
        root._applying = true
        root._status = "Aplicando retención..."
        var config = JSON.stringify({
            max_age_days: root.retentionDays,
            max_entries: root.maxEntries,
            auto_clean: root.autoClean
        })
        if (root.bridge && typeof root.bridge.applyRetention !== "undefined") {
            var result = root.bridge.applyRetention(config)
            if (result && result.ok) {
                root._status = "Eliminados " + (result.deleted_count || 0) + " registros"
                root.retentionApplied(result.deleted_count || 0)
            } else {
                root._status = result && result.error ? "Error: " + result.error : "Error al aplicar retención"
            }
        } else {
            root._status = "Bridge no disponible"
        }
        root._applying = false
    }

    onRejected: root.retentionCancelled()
}
