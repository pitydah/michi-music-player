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
    property bool saving: false
    property string errorMsg: ""

    width: parent ? parent.width : 0
    height: 48
    color: "transparent"
    Accessible.name: entry ? entry.label || "" : ""
    Accessible.description: entry ? entry.hint || "" : ""

    function load() {
        if (!root.bridge || !root.entry) return
        root.originalValue = root.bridge.getValue(root.entry.key)
        root.dirty = false
        root.saving = false
        root.errorMsg = ""
        fieldLoader.active = true
    }

    function doSave(value) {
        root.saving = true
        root.errorMsg = ""
        if (!root.bridge) { root.saving = false; return }
        var result = root.bridge.setValue(root.entry.key, value)
        if (!result.ok) {
            root.errorMsg = result.message || "Error al guardar"
        } else {
            root.dirty = (value !== root.originalValue)
            if (result.requires_restart) {
                root.errorMsg = "Requiere reiniciar la aplicación"
            }
        }
        root.saving = false
    }

    onEntryChanged: load()

    RowLayout {
        anchors.fill: parent; spacing: MichiTheme.spacing.md
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Label { text: root.entry.label || ""; elide: Text.ElideRight; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
            Label { text: root.errorMsg || root.entry.hint || ""; visible: text; color: root.errorMsg ? MichiTheme.colors.accentRed : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }
        }

        BusyIndicator { running: root.saving; visible: root.saving; width: 16; height: 16 }

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

    Component { id: textCtl
        TextField {
            text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""
            placeholderText: root.entry.placeholder || ""
            onTextEdited: debounceTimer.restart()
            Timer { id: debounceTimer; interval: 300; onTriggered: parent.doSave(parent.text) }
        }
    }

    Component { id: intCtl
        SpinBox {
            value: root.bridge ? parseInt(root.bridge.getValue(root.entry.key)) || 0 : 0
            from: root.entry.min_value !== null ? root.entry.min_value : 0
            to: root.entry.max_value !== null ? root.entry.max_value : 999999
            onValueModified: root.doSave(value)
        }
    }

    Component { id: floatCtl
        SpinBox {
            value: root.bridge ? parseInt(root.bridge.getValue(root.entry.key)) || 0 : 0
            from: root.entry.min_value || 0
            to: root.entry.max_value || 999999
            stepSize: 1
            onValueModified: root.doSave(value)
        }
    }

    Component { id: boolCtl
        Switch {
            checked: root.bridge ? root.bridge.getValue(root.entry.key) === true : false
            onClicked: root.doSave(checked)
        }
    }

    Component { id: selectCtl
        ComboBox {
            model: root.entry.options || []; textRole: "label"; valueRole: "value"
            currentIndex: {
                var val = root.bridge ? root.bridge.getValue(root.entry.key) : ""
                var opts = root.entry.options || []
                for (var i = 0; i < opts.length; i++) { if (opts[i].value === val) return i }
                return 0
            }
            onActivated: function(idx) { root.doSave(root.entry.options[idx].value) }
        }
    }

    Component { id: sliderCtl
        MichiSlider {
            width: 200
            value: root.bridge ? parseFloat(root.bridge.getValue(root.entry.key)) || 0 : 0
            from: root.entry.min_value || 0; to: root.entry.max_value || 100
            onMoved: root.doSave(value)
        }
    }

    Component { id: fileCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField { text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""; readOnly: true; Layout.fillWidth: true }
            MichiButton { text: "..."; implicitWidth: 32
                onClicked: fileDialog.open()
            }
            FileDialog { id: fileDialog
                onAccepted: { root.doSave(selectedFile.toLocalFile()) }
            }
        }
    }

    Component { id: dirCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField { text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""; readOnly: true; Layout.fillWidth: true }
            MichiButton { text: "..."; implicitWidth: 32
                onClicked: folderDialog.open()
            }
            FolderDialog { id: folderDialog
                onAccepted: { root.doSave(selectedFolder.toLocalFile()) }
            }
        }
    }

    Component { id: secretCtl
        TextField {
            text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""
            placeholderText: root.entry.placeholder || "Contraseña"
            echoMode: TextInput.Password
            onTextEdited: debounceTimerSec.restart()
            Timer { id: debounceTimerSec; interval: 300; onTriggered: parent.doSave(parent.text) }
        }
    }

    Component { id: actionCtl
        MichiButton { text: root.entry.label || "Ejecutar"; variant: "primary"
            onClicked: { if (root.bridge) { root.bridge.setValue(root.entry.key, true); root.bridge.setValue(root.entry.key, false) } }
        }
    }

    Component.onCompleted: load()
}
