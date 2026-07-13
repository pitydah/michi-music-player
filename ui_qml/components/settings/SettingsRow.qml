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

    width: parent ? parent.width : 0
    height: 48
    color: "transparent"
    Accessible.name: entry ? entry.label || "" : ""

    function load() {
        if (!root.bridge || !root.entry) return
        root.originalValue = root.bridge.getValue(root.entry.key)
        fieldLoader.active = true
    }

    onEntryChanged: load()

    RowLayout {
        anchors.fill: parent; spacing: MichiTheme.spacing.md
        Label { text: root.entry.label || ""; Layout.fillWidth: true; elide: Text.ElideRight; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        Label { text: root.entry.hint || ""; visible: root.entry.hint; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }

        Loader {
            id: fieldLoader
            active: false; visible: true
            Layout.preferredWidth: 200

            sourceComponent: {
                if (!root.entry) return null
                if (root.entry.type === "bool") return boolCtl
                if (root.entry.type === "select") return selectCtl
                if (root.entry.type === "int") return intCtl
                if (root.entry.type === "file") return fileCtl
                return textCtl
            }
        }
    }

    Component { id: textCtl
        TextField {
            text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""
            placeholderText: root.entry.placeholder || ""
            onTextEdited: { if (root.bridge) root.bridge.setValue(root.entry.key, text); root.dirty = true }
        }
    }

    Component { id: intCtl
        SpinBox {
            value: root.bridge ? parseInt(root.bridge.getValue(root.entry.key)) || 0 : 0
            from: root.entry.min_value !== null ? root.entry.min_value : 0
            to: root.entry.max_value !== null ? root.entry.max_value : 999999
            onValueModified: { if (root.bridge) root.bridge.setValue(root.entry.key, value); root.dirty = true }
        }
    }

    Component { id: boolCtl
        Switch {
            checked: root.bridge ? root.bridge.getValue(root.entry.key) === true : false
            onCheckedChanged: { if (root.bridge) root.bridge.setValue(root.entry.key, checked); root.dirty = true }
        }
    }

    Component { id: selectCtl
        ComboBox {
            model: root.entry.options || []
            textRole: "label"; valueRole: "value"
            currentIndex: {
                var val = root.bridge ? root.bridge.getValue(root.entry.key) : ""
                var opts = root.entry.options || []
                for (var i = 0; i < opts.length; i++) {
                    if (opts[i].value === val) return i
                }
                return 0
            }
            onActivated: function(index) {
                var val = root.entry.options[index].value
                if (root.bridge) root.bridge.setValue(root.entry.key, val)
                root.dirty = true
            }
        }
    }

    Component { id: fileCtl
        RowLayout { spacing: MichiTheme.spacing.xs
            TextField {
                text: root.bridge ? root.bridge.getValue(root.entry.key) || "" : ""
                placeholderText: root.entry.placeholder || "Seleccionar carpeta..."
                Layout.fillWidth: true; readOnly: true
            }
            MichiButton { text: "..."; variant: "ghost"; implicitWidth: 32
                onClicked: fileDialog.open()
            }
            FolderDialog { id: fileDialog
                onAccepted: {
                    var folderPath = selectedFolder.toLocalFile()
                    if (root.bridge) root.bridge.setValue(root.entry.key, folderPath)
                    root.dirty = true
                }
            }
        }
    }

    Component.onCompleted: load()
}
