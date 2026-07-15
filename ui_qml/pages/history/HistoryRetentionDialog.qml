import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import "../../theme"
import "../../components"

Dialog {
    id: root

    property var bridge: null
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property int _retentionDays: 365
    property int _maxEntries: 0
    property bool _autoClean: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property int retentionDays: 365
    property int maxEntries: 10000
    property bool autoClean: false
=======
    property int _retentionDays: 365
    property int _maxEntries: 0
    property bool _autoClean: false
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    property bool _applying: false
    property int _currentCount: 0
    property string _oldestDate: ""
    property string _status: ""

    signal retentionApplied(int deletedCount)
    signal retentionCancelled()

    title: "Política de retención"
    modal: true
    x: (parent.width - width) / 2
    y: (parent.height - height) / 3
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    width: 380
    objectName: "historyRetentionDialog"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    objectName: "history.retentionDialog"
    closePolicy: Dialog.CloseOnEscape

>>>>>>> Stashed changes
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
            text: "Configurar retención del historial de reproducción"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Mantener registros de:"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            ComboBox {
                id: daysCombo
                Layout.preferredWidth: 140
                model: [
                    {text: "30 días", value: 30},
                    {text: "60 días", value: 60},
                    {text: "90 días", value: 90},
                    {text: "180 días", value: 180},
                    {text: "365 días", value: 365},
                    {text: "Siempre", value: -1}
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: {
                    var vals = [30, 60, 90, 180, 365, -1]
                    var idx = vals.indexOf(root._retentionDays)
                    return idx >= 0 ? idx : 4
                }
                objectName: "retentionDaysCombo"
                Accessible.name: "Días de retención"
                onCurrentValueChanged: {
                    if (currentValue > 0) root._retentionDays = currentValue
                    else root._retentionDays = -1
                }
            }
        }

<<<<<<< Updated upstream
=======
                Text {
                    text: "días"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
=======
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
            text: "Configurar retención del historial de reproducción"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Mantener registros de:"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            ComboBox {
                id: daysCombo
                Layout.preferredWidth: 140
                model: [
                    {text: "30 días", value: 30},
                    {text: "60 días", value: 60},
                    {text: "90 días", value: 90},
                    {text: "180 días", value: 180},
                    {text: "365 días", value: 365},
                    {text: "Siempre", value: -1}
                ]
                textRole: "text"
                valueRole: "value"
                currentIndex: {
                    var vals = [30, 60, 90, 180, 365, -1]
                    var idx = vals.indexOf(root._retentionDays)
                    return idx >= 0 ? idx : 4
                }
                objectName: "retentionDaysCombo"
                Accessible.name: "Días de retención"
                onCurrentValueChanged: {
                    if (currentValue > 0) root._retentionDays = currentValue
                    else root._retentionDays = -1
                }
            }
        }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Máximo de entradas:"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            SpinBox {
                id: maxSpin
                from: 0
                to: 100000
                stepSize: 1000
                value: root._maxEntries > 0 ? root._maxEntries : 0
                objectName: "retentionMaxSpin"
                Accessible.name: "Máximo de entradas"
                onValueChanged: root._maxEntries = value
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                text: "(0 = sin límite)"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                id: autoCleanCheck
                checked: root._autoClean
                text: "Limpiar automáticamente"
                objectName: "autoCleanCheck"
                Accessible.name: "Limpiar automáticamente"
                onCheckedChanged: root._autoClean = checked
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: "Estado actual:"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            text: "Entradas: " + root._currentCount
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
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                objectName: "retentionCancelButton"
                Accessible.name: "Cancelar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { root.reject(); root.close() }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                text: "Los registros anteriores a " + root.retentionDays + " días serán eliminados permanentemente."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                wrapMode: Text.WordWrap
                width: parent.width
=======
                text: "(0 = sin límite)"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
>>>>>>> origin/michi-qml-functional-wave
            }

<<<<<<< HEAD
            Text {
                text: root._status
                color: root._status.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                Accessible.role: Accessible.StatusBar
                Accessible.name: root._status
>>>>>>> Stashed changes
            }

            MichiButton {
                text: "Guardar"
                variant: "primary"
                enabled: !root._applying
                objectName: "retentionSaveButton"
                Accessible.name: "Guardar configuración de retención"
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

<<<<<<< Updated upstream
=======
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
=======
        RowLayout {
            Layout.fillWidth: true
            CheckBox {
                id: autoCleanCheck
                checked: root._autoClean
                text: "Limpiar automáticamente"
                objectName: "autoCleanCheck"
                Accessible.name: "Limpiar automáticamente"
                onCheckedChanged: root._autoClean = checked
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: "Estado actual:"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            text: "Entradas: " + root._currentCount
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
            font.pixelSize: MichiTheme.typography.metaSize
            visible: text !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignRight
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                objectName: "retentionCancelButton"
                Accessible.name: "Cancelar"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { root.reject(); root.close() }
            }

            MichiButton {
                text: "Guardar"
                variant: "primary"
                enabled: !root._applying
                objectName: "retentionSaveButton"
                Accessible.name: "Guardar configuración de retención"
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    onOpened: {
        root.loadSettings()
        root._status = ""
    }

    onClosed: {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        root._applying = false
    }

    QQC2.FocusTrap {
        active: root.opened
    }

    Keys.onEscapePressed: {
        root.reject()
        root.close()
    }
}
