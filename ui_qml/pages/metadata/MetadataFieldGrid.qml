import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Field Grid"
    objectName: "metadataFieldGrid"
    focus: true
    id: root

    property var mb: null
    property bool editable: false
    property var _fieldValues: ({})

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Campos de metadatos"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Repeater {
                    model: root.mb ? root.mb.fields : []

                    MetadataFieldRow {
                        width: parent.width
                        fieldLabel: modelData.label || ""
                        fieldValue: root.editable ? (root._fieldValues[modelData.key] !== undefined ? root._fieldValues[modelData.key] : modelData.value) : modelData.value
                        fieldKey: modelData.key
                        editable: root.editable && ["text", "int"].indexOf(modelData.type) >= 0
                        onValueChanged: {
                            root._fieldValues[fieldKey] = newValue
                            if (root.mb && typeof root.mb.setField !== "undefined")
                                root.mb.setField(fieldKey, newValue)
                        }
                    }
                }

                Text {
                    text: root.mb && root.mb.fields.length === 0 ? "Carga un archivo para ver sus metadatos." : ""
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }
            }
        }

        StatusBadge {
            text: root.mb && root.mb.errorMessage ? root.mb.errorMessage : ""
            kind: "error"
            visible: text !== ""
        }
    }
}
