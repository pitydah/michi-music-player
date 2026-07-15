import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var doc: null
    property bool _running: false
    property int _dryRunProgress: 0
    property int _dryRunTotal: 0

    signal confirmRepair()
    signal cancelRepair()

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Vista previa de reparación"; width: parent.width }

        GlassMaterial {
            width: parent.width
            radius: MichiTheme.radiusMd
            variant: root._running ? "accent" : "base"
            visible: root.doc && root.doc.issues.length > 0

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.md

                Text {
                    text: root._running
                          ? "Analizando reparaciones..."
                          : "Revisa los cambios antes de aplicarlos."
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                MichiProgressBar {
                    width: parent.width
                    value: root._dryRunTotal > 0
                           ? root._dryRunProgress / root._dryRunTotal * 100 : 0
                    indeterminate: root._running && root._dryRunTotal === 0
                    visible: root._running
                }

                Repeater {
                    model: root.doc ? root.doc.issues : []

                    Item {
                        width: parent.width; height: 24
                        visible: modelData.selected
                        Text {
                            text: "→ " + (modelData.type || "") + ": " + (modelData.detail || "")
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                Text {
                    text: {
                        if (!root.doc) return ""
                        var count = 0
                        if (root.doc._selected_ids)
                            count = root.doc._selected_ids.length
                        else
                            count = root.doc.issues.filter(function(i) { return i.selected }).length
                        return "Seleccionados: " + count
                    }
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        text: root._running ? "Procesando..." : "Confirmar reparación"
                        variant: "danger"
                        enabled: !root._running
                        objectName: "libraryDoctor.confirmRepairButton"
                        Accessible.name: "Confirmar reparación de problemas seleccionados"
                        onClicked: {
                            root._running = true
                            root.confirmRepair()
                        }
                    }

                    MichiButton {
                        text: "Cancelar"
                        variant: "ghost"
                        enabled: !root._running
                        objectName: "libraryDoctor.cancelRepairButton"
                        Accessible.name: "Cancelar reparación"
                        onClicked: {
                            root._running = false
                            root.cancelRepair()
                        }
                    }
                }
            }
        }
    }

    function reset() {
        root._running = false
        root._dryRunProgress = 0
        root._dryRunTotal = 0
    }
}
