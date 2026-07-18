import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
    property int _retentionDays: 365
    property int _maxEntries: 0
    property bool _autoClean: false
    property bool _applying: false
    property int _currentCount: 0
    property string _oldestDate: ""
    property string _status: ""

    signal retentionApplied(int deletedCount)
    signal retentionCancelled()

    title: qsTr("Política de retención")
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
    width: 380
    objectName: "historyRetentionDialog"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Política de retención"
    closePolicy: Popup.CloseOnEscape

    function loadSettings() {
        if (!root.bridge || !root.bridge.historyQueryService ||
            typeof root.bridge.historyQueryService.getRetentionSettings === "undefined") return
        var settings = root.bridge.historyQueryService.getRetentionSettings()
        if (settings && settings.ok) {
            root._retentionDays = settings.retention_days || 365
            root._maxEntries = settings.max_entries || 0
            root._autoClean = settings.auto_clean || false
        }
        root._currentCount = root.bridge ? root.bridge.historyCount : 0
    }

    ColumnLayout {
        spacing: MichiTheme.spacing.md
        width: parent ? parent.width : 360

        Text {
            text: qsTr("Configurar retención del historial de reproducción")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: qsTr("Mantener registros de:")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            ComboBox {
                Accessible.role: Accessible.ComboBox
                Accessible.name: "Período de retención"
                activeFocusOnTab: true
                focusPolicy: Qt.StrongFocus
                id: daysCombo
                Layout.preferredWidth: 140
                model: [
                    {text: qsTr("30 días"), value: 30},
                    {text: qsTr("60 días"), value: 60},
                    {text: qsTr("90 días"), value: 90},
                    {text: qsTr("180 días"), value: 180},
                    {text: qsTr("365 días"), value: 365},
                    {text: qsTr("Siempre"), value: -1}
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: {
                    var vals = [30, 60, 90, 180, 365, -1]
                    var idx = vals.indexOf(root._retentionDays)
                    return idx >= 0 ? idx : 4
                }
                onCurrentValueChanged: {
                    if (currentValue > 0) root._retentionDays = currentValue
                    else root._retentionDays = -1
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: qsTr("Máximo de entradas:")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            SpinBox {
                focusPolicy: Qt.StrongFocus
                id: maxSpin
                from: 0
                to: 100000
                stepSize: 1000
                value: root._maxEntries > 0 ? root._maxEntries : 0
                onValueChanged: root._maxEntries = value
            }
            Text {
                text: qsTr("(0 = sin límite)")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                id: autoCleanCheck
                checked: root._autoClean
                text: qsTr("Limpiar automáticamente")
                onCheckedChanged: root._autoClean = checked
            }
        }

        Rectangle {
    focus: true
            Layout.fillWidth: true
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: qsTr("Estado actual:")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            text: qsTr("Entradas: ") + root._currentCount
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
        }

        Text {
            text: root._retentionDays > 0 ? "Los registros anteriores a " + root._retentionDays +
                  " días serán eliminados permanentemente." : "Todos los registros se conservarán indefinidamente."
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Text {
            text: root._status
            color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
                Accessible.role: Accessible.Button

            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: qsTr("Cancelar")
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { root.reject(); root.close() }
            }

            MichiButton {
                text: qsTr("Guardar")
                variant: "primary"
                enabled: !root._applying
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: {
                    root._applying = true
                    root._status = ""
                    if (root.bridge && typeof root.bridge.historyQueryService !== "undefined" &&
                        root.bridge.historyQueryService &&
                        typeof root.bridge.historyQueryService.applyRetention !== "undefined") {
                        var result = root.bridge.historyQueryService.applyRetention(
                            root._retentionDays > 0 ? root._retentionDays : 36500,
                            root._maxEntries > 0 ? root._maxEntries : 0)
                        if (result && result.ok) {
                            var deleted = result.deleted_count || 0
                            root._status = "Eliminados " + deleted + " registros"
                            root._currentCount = root.bridge ? root.bridge.historyCount : 0
                            root.retentionApplied(deleted)
                        } else {
                            root._status = result && result.error ? "Error: " + result.error : "Error al aplicar retención"
                        }
                    } else {
                        root.retentionApplied(0)
                    }
                    root._applying = false
                    root.close()
                }
            }
        }
    }

    onOpened: {
        root.loadSettings()
        root._status = ""
    }

    onClosed: {
        root._applying = false
    }

    Item {
        focus: root.opened
    }

    Keys.onEscapePressed: {
        root.reject()
        root.close()
    }
}
