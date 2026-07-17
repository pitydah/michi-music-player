import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Row"
    objectName: "settingsRow"
    focus: true
    id: root
    property var entry: null
    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property bool dirty: false
    property var originalValue: null
    property var editedValue: null
    property var appliedValue: null
    property bool saving: false
    property string errorMsg: ""
    property string restartMsg: ""
    property bool _debounceActive: false
    property var _debounceTimer: null
    property var _sliderPreview: null

    signal clicked()

    width: parent ? parent.width : 0
    implicitHeight: 56
    color: root.dirty ? MichiTheme.colors.accentSurface : "transparent"
    radius: MichiTheme.radius.sm
    Accessible.description: entry ? entry.hint || "" : ""
    Accessible.onPressAction: root.doSave(root.editedValue !== null ? root.editedValue : root.originalValue)

    function load() {
        if (!root.bridge || !root.entry) return
        root.originalValue = root.bridge.getValue(root.entry.key)
        root.editedValue = null
        root.appliedValue = root.originalValue
        root.dirty = false
        root.saving = false
        root.errorMsg = ""
        root.restartMsg = ""
        fieldLoader.active = true
    }

    function doSave(value) {
        if (_debounceActive && _debounceTimer) {
            _debounceTimer.stop()
        }
        root.saving = true
        root.errorMsg = ""
        root.restartMsg = ""
        root.editedValue = value
        if (!root.bridge) { root.saving = false; return }
        var result = root.bridge.setValue(root.entry.key, value)
        if (!result.ok) {
            root.errorMsg = result.message || "Error al guardar"
            root.appliedValue = root.originalValue
            if (_sliderPreview !== null && !result.ok) {
                _sliderPreview.value = root.originalValue
            }
        } else {
            root.appliedValue = value
            root.dirty = (value !== root.originalValue)
            if (result.requires_restart) {
                root.restartMsg = "Requiere reiniciar la aplicación"
            }
        }
        root.saving = false
    }

    function scheduleSave(value) {
        root.editedValue = value
        if (root.entry && root.entry.type === "slider") return
        if (_debounceTimer) _debounceTimer.stop()
        _debounceTimer = Qt.createQmlObject("import QtQuick; Timer {}", root)
        _debounceTimer.interval = 300
        _debounceTimer.repeat = false
        _debounceTimer.triggered.connect(function() {
            root.doSave(value)
            _debounceActive = false
        })
        _debounceActive = true
        _debounceTimer.start()
    }

    function cancelDebounce() {
        if (_debounceActive && _debounceTimer) {
            _debounceTimer.stop()
            _debounceActive = false
        }
    }

    function sliderCommit(value) {
        root.doSave(value)
    }

    function sliderPreviewUpdate(value) {
        root.editedValue = value
    }

    onEntryChanged: load()

    RowLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.md
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Label {
                text: root.entry.label || ""
                elide: Text.ElideRight
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
            }
            Label {
                text: {
                    if (root.errorMsg) return root.errorMsg
                    if (root.restartMsg) return root.restartMsg
                    return root.entry.hint || ""
                }
                visible: text
                color: root.errorMsg ? MichiTheme.colors.error : root.restartMsg ? MichiTheme.colors.warning : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }
        }

        Rectangle {
            visible: root.dirty; width: 8; height: 8; radius: MichiTheme.radius.sm
            color: MichiTheme.colors.warning; Layout.alignment: Qt.AlignVCenter
        }

        BusyIndicator { running: root.saving; visible: root.saving; width: 16; height: 16; Layout.alignment: Qt.AlignVCenter }

        Loader {
            id: fieldLoader; active: false
            Layout.preferredWidth: root.entry && root.entry.type === "bool" ? 48 : 200
            sourceComponent: {
                if (!root.entry) return null
                if (root.entry.type === "bool") return boolCtl
                if (root.entry.type === "select" || root.entry.type === "enum") return selectCtl
                if (root.entry.type === "int") return intCtl
                if (root.entry.type === "float") return floatCtl
                if (root.entry.type === "slider" || root.entry.type === "range") return sliderCtl
                if (root.entry.type === "file") return fileCtl
                if (root.entry.type === "directory" || root.entry.type === "path") return dirCtl
                if (root.entry.type === "secret") return secretCtl
                if (root.entry.type === "action") return actionCtl
                if (root.entry.type === "color") return colorCtl
                if (root.entry.type === "multi-select") return multiSelectCtl
                return textCtl
            }
        }
    }

    MouseArea {
        anchors.fill: parent; acceptedButtons: Qt.NoButton; hoverEnabled: false
    }

    Component { id: textCtl
        TextField {
            Accessible.role: Accessible.EditableText

            Accessible.name: "Campo de texto"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            text: root.originalValue !== null ? String(root.originalValue) : ""
            placeholderText: root.entry.placeholder || ""
            onTextEdited: root.scheduleSave(text)
        }
    }
            Accessible.role: Accessible.EditableText

            Accessible.name: "SpinBox"

            activeFocusOnTab: true


    Component { id: intCtl
        SpinBox {
            focusPolicy: Qt.StrongFocus
            value: root.originalValue !== null ? parseInt(root.originalValue) || 0 : 0
            from: root.entry.min_value !== null ? root.entry.min_value : 0
            to: root.entry.max_value !== null ? root.entry.max_value : 999999
            editable: true
            Accessible.role: Accessible.Pane

            activeFocusOnTab: true

            onValueModified: root.doSave(value)
        }
    }

    Component { id: floatCtl
        MichiDoubleSpinBox {
            value: root.originalValue !== null ? parseFloat(root.originalValue) || 0 : 0
            Accessible.role: Accessible.CheckBox

            Accessible.name: "Switch"

            Accessible.checked: root.checked

            activeFocusOnTab: true

            from: root.entry.min_value || 0
            to: root.entry.max_value || 999999
            onValueModified: root.doSave(value)
            Accessible.role: Accessible.ComboBox

            Accessible.name: "ComboBox"

            activeFocusOnTab: true

        }
    }

    Component { id: boolCtl
        Switch {
            checked: root.originalValue === true || root.originalValue === "true"
            onClicked: root.doSave(checked)
        }
    }

    Component { id: selectCtl
        ComboBox {
            focusPolicy: Qt.StrongFocus
            model: root.entry.options || []
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                var val = root.originalValue
                var opts = root.entry.options || []
                for (var i = 0; i < opts.length; i++) {
                Accessible.role: Accessible.Slider

                activeFocusOnTab: true

                    if (String(opts[i].value) === String(val)) return i
                }
                return 0
            }
            onActivated: function(idx) {
                root.doSave(root.entry.options[idx].value)
            }
        }
    }

    Component { id: sliderCtl
        RowLayout {
            spacing: MichiTheme.spacing.sm
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

            Layout.fillWidth: true
            MichiSlider {
                id: slider
                Layout.fillWidth: true
                value: root.originalValue !== null ? parseFloat(root.originalValue) || 0 : 0
                from: root.entry.min_value || 0
                to: root.entry.max_value || 100
                onPressedChanged: {
                    if (!pressed) {
                        root.sliderCommit(value)
                    }
                }
                onMoved: {
                    root.sliderPreviewUpdate(value)
                }
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: sliderEditor
                implicitWidth: 64
                text: slider.value.toFixed(root.entry.type === "range" ? 2 : 0)
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: MichiTheme.typography.captionSize
                color: MichiTheme.colors.textPrimary
                background: Rectangle {
                    color: MichiTheme.colors.surfaceInput
                    radius: MichiTheme.radius.sm
                    border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                    border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                }
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

                validator: DoubleValidator {
                    bottom: slider.from
                    top: slider.to
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                }
                onEditingFinished: {
                    var v = parseFloat(text)
                    if (!isNaN(v)) {
                        v = Math.max(slider.from, Math.min(slider.to, v))
                        slider.value = v
                        root.sliderCommit(v)
                    }
                    text = slider.value.toFixed(root.entry.type === "range" ? 2 : 0)
                }
            }
        }
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

    }

    Component { id: fileCtl
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

        RowLayout { spacing: MichiTheme.spacing.xs
            TextField {
                focusPolicy: Qt.StrongFocus
                text: root.originalValue || ""
                readOnly: true
                Layout.fillWidth: true
            }
            MichiButton {
                text: "..."
                implicitWidth: 32
                onClicked: fileDialog.open()
            Accessible.role: Accessible.EditableText

            Accessible.name: "Campo de texto"

            activeFocusOnTab: true

            }
            FileDialog {
                id: fileDialog
                onAccepted: root.doSave(selectedFile.toLocalFile())
            }
        }
                    Accessible.role: Accessible.CheckBox

                    Accessible.name: "CheckBox"

                    Accessible.checked: root.checked

                    activeFocusOnTab: true

    }

    Component { id: dirCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField {
            Accessible.role: Accessible.Button

            activeFocusOnTab: true

                focusPolicy: Qt.StrongFocus
                text: root.originalValue || ""
                readOnly: true
                Layout.fillWidth: true
            }
            MichiButton {
                text: "..."
                implicitWidth: 32
                onClicked: folderDialog.open()
            }
            FolderDialog {
                id: folderDialog
                onAccepted: root.doSave(selectedFolder.toLocalFile())
            }
        }
    }

                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

    Component { id: secretCtl
        TextField {
            focusPolicy: Qt.StrongFocus
            text: root.originalValue || ""
            placeholderText: root.entry.placeholder || "Contraseña"
            echoMode: revealButton.checked ? TextInput.Normal : TextInput.Password
            onTextEdited: root.scheduleSave(text)
            RowLayout {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: MichiTheme.spacing.xs
                CheckBox {
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                    id: revealButton
                activeFocusOnTab: true

                    text: ""
                }
            }
        }
    }

    Component { id: actionCtl
        MichiButton {
            text: root.entry.label || "Ejecutar"
            variant: "primary"
            onClicked: {
                if (root.bridge) {
                    root.bridge.setValue(root.entry.key, true)
                    root.bridge.setValue(root.entry.key, false)
                }
            }
        }
    }

    Component { id: colorCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            Rectangle {
                implicitWidth: 32; implicitHeight: 32; radius: MichiTheme.radius.sm
                color: root.originalValue || MichiTheme.colors.accent
                border.width: 1; border.color: MichiTheme.colors.borderCard
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                text: root.originalValue || MichiTheme.colors.accent
                Layout.fillWidth: true
                font.pixelSize: MichiTheme.typography.captionSize
                onTextEdited: root.scheduleSave(text)
            }
        }
    }

    Component { id: multiSelectCtl
        RowLayout {
            spacing: MichiTheme.spacing.xs
            Layout.fillWidth: true
            TextField {
                focusPolicy: Qt.StrongFocus
                text: root.originalValue ? String(root.originalValue) : ""
                readOnly: true
                Layout.fillWidth: true
            }
        }
    }

    Component.onCompleted: load()
}
