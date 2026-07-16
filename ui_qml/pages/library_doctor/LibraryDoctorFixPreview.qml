import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Fix Preview"
    objectName: "libraryDoctorFixPreview"
    focus: true
    id: root

    property var doc: null
    property bool _confirmRepair: false

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Reparación"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                Text {
                    text: "Vista previa de reparaciones"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: "Selecciona los problemas a reparar y revisa los cambios antes de aplicarlos."
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap; width: parent.width
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: "Seleccionar todos"
                        variant: "ghost"
                        onClicked: { if (root.doc) root.doc.selectAll() }
                    }
                    MichiButton {
                        text: "Deseleccionar todos"
                        variant: "ghost"
                        onClicked: { if (root.doc) root.doc.selectNone() }
                    }
                }

                Repeater {
                    model: root.doc ? root.doc.issues : []

                    Item {
                        width: parent.width; height: 24
                        visible: modelData.selected
                        Text {
                            text: "→ " + (modelData.type || "") + ": " + (modelData.detail || "")
                            color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; width: parent.width
                        }
                    }
                }

                Text {
                    text: root.doc && root.doc._selected_ids ? "Seleccionados: " + root.doc._selected_ids.length : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root._confirmRepair ? "Confirmar reparación" : "Ejecutar reparación (dry-run)"
                        variant: root._confirmRepair ? "danger" : "primary"
                        enabled: root.doc && root.doc._selected_ids && root.doc._selected_ids.length > 0
                        onClicked: {
                            if (!root._confirmRepair) {
                                root._confirmRepair = true
                            } else {
                                root._confirmRepair = false
                                if (root.doc && typeof root.doc.repairSelected !== "undefined")
                                    root.doc.repairSelected()
                            }
                        }
                    }
                    MichiButton {
                        text: "Cancelar"
                        variant: "ghost"
                        visible: root._confirmRepair
                        onClicked: root._confirmRepair = false
                    }
                }
            }
        }
    }
}
