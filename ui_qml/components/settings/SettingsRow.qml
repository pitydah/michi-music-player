import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../"

Rectangle {
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

    signal clicked()

    width: parent ? parent.width : 0
    implicitHeight: 56
    color: root.dirty ? Qt.rgba(0.561, 0.718, 1.0, 0.04) : "transparent"
    radius: MichiTheme.radius.sm
    Accessible.name: entry ? entry.label || "" : ""
    Accessible.description: entry ? entry.hint || "" : ""
    Accessible.role: Accessible.Button
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
        if (root.entry.type === "slider") return
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
                color: root.errorMsg ? "#F87171" : root.restartMsg ? "#FBBF24" : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
            }
        }

        Rectangle {
            visible: root.dirty; width: 8; height: 8; radius: 4
            color: "#FBBF24"; Layout.alignment: Qt.AlignVCenter
        }

        BusyIndicator { running: root.saving; visible: root.saving; width: 16; height: 16; Layout.alignment: Qt.AlignVCenter }

        Loader {
            id: fieldLoader; active: false
            Layout.preferredWidth: root.entry.type === "bool" ? 48 : 200
            sourceComponent: {
                if (!root.entry) return null
                if (root.entry.type === "bool") return boolCtl
                if (root.entry.type === "select") return selectCtl
                if (root.entry.type === "int") return intCtl
                if (root.entry.type === "float") return floatCtl
                if (root.entry.type === "slider") return sliderCtl
                if (root.entry.type === "file") return fileCtl
                if (root.entry.type === "directory") return dirCtl
                if (root.entry.type === "secret") return secretCtl
                if (root.entry.type === "action") return actionCtl
                return textCtl
            }
        }
    }

    MouseArea {
        anchors.fill: parent; acceptedButtons: Qt.NoButton; hoverEnabled: false
    }

    Component { id: textCtl
        TextField {
            text: root.originalValue !== null ? String(root.originalValue) : ""
            placeholderText: root.entry.placeholder || ""
            onTextEdited: root.scheduleSave(text)
            Accessible.role: Accessible.EditableText
            Accessible.name: root.entry ? root.entry.label + " campo de texto" : ""
        }
    }

    Component { id: intCtl
        SpinBox {
            value: root.originalValue !== null ? parseInt(root.originalValue) || 0 : 0
            from: root.entry.min_value !== null ? root.entry.min_value : 0
            to: root.entry.max_value !== null ? root.entry.max_value : 999999
            editable: true
            onValueModified: root.doSave(value)
            Accessible.role: Accessible.SpinBox
            Accessible.name: root.entry ? root.entry.label + " número" : ""
        }
    }

    Component { id: floatCtl
        SpinBox {
            value: root.originalValue !== null ? parseFloat(root.originalValue) || 0 : 0
            from: root.entry.min_value || 0
            to: root.entry.max_value || 999999
            stepSize: 1
            editable: true
            onValueModified: root.doSave(value)
            Accessible.role: Accessible.SpinBox
            Accessible.name: root.entry ? root.entry.label + " decimal" : ""
        }
    }

    Component { id: boolCtl
        Switch {
            checked: root.originalValue === true || root.originalValue === "true"
            onClicked: root.doSave(checked)
            Accessible.role: Accessible.CheckBox
            Accessible.name: root.entry ? root.entry.label : ""
        }
    }

    Component { id: selectCtl
        ComboBox {
            model: root.entry.options || []
            textRole: "label"
            valueRole: "value"
            currentIndex: {
                var val = root.originalValue
                var opts = root.entry.options || []
                for (var i = 0; i < opts.length; i++) {
                    if (String(opts[i].value) === String(val)) return i
                }
                return 0
            }
            onActivated: function(idx) {
                root.doSave(root.entry.options[idx].value)
            }
            Accessible.role: Accessible.ComboBox
            Accessible.name: root.entry ? root.entry.label : ""
        }
    }

    Component { id: sliderCtl
        MichiSlider {
            width: 200
            value: root.originalValue !== null ? parseFloat(root.originalValue) || 0 : 0
            from: root.entry.min_value || 0
            to: root.entry.max_value || 100
            onMoved: root.doSave(value)
            onPressedChanged: {
                if (!pressed && value !== parseFloat(root.originalValue)) {
                    root.doSave(value)
                }
            }
            Accessible.role: Accessible.Slider
            Accessible.name: root.entry ? root.entry.label : ""
        }
    }

    Component { id: fileCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField {
                text: root.originalValue || ""
                readOnly: true
                Layout.fillWidth: true
            }
            MichiButton {
                text: "..."
                implicitWidth: 32
                onClicked: fileDialog.open()
            }
            FileDialog {
                id: fileDialog
                onAccepted: root.doSave(selectedFile.toLocalFile())
            }
        }
    }

    Component { id: dirCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField {
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

    Component { id: secretCtl
        TextField {
            text: root.originalValue || ""
            placeholderText: root.entry.placeholder || "Contraseña"
            echoMode: revealButton.checked ? TextInput.Normal : TextInput.Password
            onTextEdited: root.scheduleSave(text)
            Accessible.role: Accessible.EditableText
            Accessible.name: root.entry ? root.entry.label + " contraseña" : ""
            RowLayout {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 4
                CheckBox {
                    id: revealButton
                    text: ""
                    Accessible.name: "Mostrar contraseña"
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
            Accessible.role: Accessible.Button
            Accessible.name: root.entry ? root.entry.label : ""
        }
    }

    Component.onCompleted: load()
}
