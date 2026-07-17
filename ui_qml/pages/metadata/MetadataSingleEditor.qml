import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Single Editor"
    objectName: "metadataSingleEditor"
    focus: true
    id: root

    property var mb: null
    property string selectedFile: ""
    property bool _editing: false
    property bool _confirmSave: false

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.lg

        GlassCard {
            width: parent.width
            title: "Archivo"
            subtitle: root.selectedFile ? root.selectedFile.split("/").pop() : "Ninguno"
            variant: root.selectedFile ? "accent" : "base"
        }

        Row {
            spacing: MichiTheme.spacing.sm
            MichiButton {
                text: root._editing ? "Cancelar edición" : "Editar campos"
                variant: root._editing ? "ghost" : "primary"
                onClicked: root._editing = !root._editing
            }
            MichiButton {
                text: root.editing ? "Guardar cambios" : "Guardar"
                variant: "secondary"
                visible: root._editing
                onClicked: {
                    if (root.mb && typeof root.mb.saveChanges !== "undefined")
                        root.mb.saveChanges()
                    root._editing = false
                }
            }
            MichiButton {
                text: "Refrescar"
                variant: "ghost"
                onClicked: { if (root.mb) root.mb.refresh() }
            }
        }

        MetadataFieldGrid {
            width: parent.width
            mb: root.mb
            editable: root._editing
        }

        MetadataArtworkEditor {
            width: parent.width
            mb: root.mb
            visible: root.selectedFile !== ""
        }

        MetadataPreview {
            width: parent.width
            mb: root.mb
        }

        MetadataWriteProgress {
            width: parent.width
            mb: root.mb
        }
    }
}
