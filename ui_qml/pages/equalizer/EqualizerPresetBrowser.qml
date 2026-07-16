import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Equalizer Preset Browser"
    objectName: "equalizerPresetBrowser"
    focus: true
    id: root

    property var eqBridge: null
    property var notif: null
    property bool _showCustom: false
    property string _customName: ""

    function _notify(msg, kind) {
        if (root.notif) root.notif.showMessage(msg, kind)
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        Repeater {
            model: root.eqBridge ? root.eqBridge.presets : []

            GlassCard {
                width: parent.width; height: 50
                title: modelData.name || ""
                subtitle: modelData.bands ? modelData.bands.length + " bandas" : ""
                variant: modelData.name === (root.eqBridge ? root.eqBridge.currentPreset : "") ? "accent" : "base"
                interactive: root.enabled
                onClicked: {
                    if (root.eqBridge) {
                        var r = root.eqBridge.applyPreset(modelData.name)
                        if (r.ok && root.notif)
                            root.notif.showMessage("Preset: " + modelData.name, "success")
                        else if (!r.ok && root.notif)
                            root.notif.showMessage(r.message || r.error, "error")
                    }
                }
            }
        }

        MichiButton {
            text: root._showCustom ? "Cancelar" : "Guardar como preset personalizado"
            variant: "ghost"
            visible: root.enabled
            onClicked: root._showCustom = !root._showCustom
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
            visible: root._showCustom && root.enabled

            SearchField {
                id: nameField
                width: parent.width * 0.6
                placeholderText: "Nombre del preset"
                onTextChangedByUser: root._customName = text
            }

            MichiButton {
                text: "Guardar"
                variant: "primary"
                enabled: root._customName.trim() !== ""
                onClicked: {
                    if (root.eqBridge) {
                        var r = root.eqBridge.saveCustomPreset(root._customName.trim())
                        if (r.ok) {
                            root._notify("Preset guardado: " + root._customName, "success")
                            root._showCustom = false
                            root._customName = ""
                            nameField.text = ""
                        } else {
                            root._notify(r.error, "error")
                        }
                    }
                }
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            visible: root.enabled

            MichiButton {
                text: "Importar preset"
                variant: "ghost"
                onClicked: importDialog.open()
            }

            MichiButton {
                text: "Exportar preset"
                variant: "ghost"
                enabled: root.eqBridge && root.eqBridge.currentPreset !== ""
                onClicked: exportDialog.open()
            }
        }

        FileDialog {
            id: importDialog
            title: "Importar preset EQ"
            nameFilters: ["Archivos EQ (*.json)", "Todos (*)"]
            onAccepted: {
                if (root.eqBridge) {
                    var r = root.eqBridge.importPreset(selectedFile.toString().replace("file://", ""))
                    if (r.ok) root._notify("Preset importado: " + (r.name || ""), "success")
                    else root._notify(r.error, "error")
                }
            }
        }

        FileDialog {
            id: exportDialog
            title: "Exportar preset EQ"
            nameFilters: ["Archivos EQ (*.json)", "Todos (*)"]
            fileMode: FileDialog.SaveFile
            onAccepted: {
                if (root.eqBridge) {
                    var r = root.eqBridge.exportPreset(selectedFile.toString().replace("file://", ""))
                    if (r.ok) root._notify("Preset exportado", "success")
                    else root._notify(r.error, "error")
                }
            }
        }
    }
}
