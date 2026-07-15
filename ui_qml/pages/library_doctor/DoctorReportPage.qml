import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var doc: null
    property int fixedCount: 0
    property int failedCount: 0
    property int skippedCount: 0
    property var _details: []

    signal exportReport()
    signal undoAll()

    implicitHeight: column.height + MichiTheme.spacing.lg

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Reporte final"; width: parent.width }

        GlassMaterial {
            width: parent.width
            radius: MichiTheme.radiusMd
            variant: root.failedCount > 0 ? "status" : "base"
            visible: root.fixedCount > 0 || root.failedCount > 0 || root.skippedCount > 0

            Column {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Resumen de reparación"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { width: 1; height: MichiTheme.spacing.sm }

                Row {
                    spacing: MichiTheme.spacing.xl
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: "Reparados"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: String(root.fixedCount); color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: "Fallidos"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: String(root.failedCount); color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: "Omitidos"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: String(root.skippedCount); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.sectionTitleSize }
                    }
                }

                Item { width: 1; height: MichiTheme.spacing.sm }

                Text {
                    text: "Detalle por archivo:"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                    visible: root._details.length > 0
                }

                Repeater {
                    model: root._details

                    Rectangle {
                        width: parent.width; height: 24
                        color: "transparent"
                        Text {
                            text: modelData.filepath
                                  ? (modelData.status + ": " + modelData.filepath)
                                  : ""
                            color: modelData.status === "ok"
                                   ? MichiTheme.colors.success
                                   : (modelData.status === "failed"
                                      ? MichiTheme.colors.error
                                      : MichiTheme.colors.textMuted)
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                Item { width: 1; height: MichiTheme.spacing.sm }

                Row {
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        text: "Exportar reporte"
                        variant: "primary"
                        objectName: "doctorExportReportButton"
                        Accessible.name: "Exportar reporte de reparación"
                        onClicked: root.exportReport()
                    }

                    MichiButton {
                        text: "Deshacer todo"
                        variant: "danger"
                        enabled: root.fixedCount > 0
                        objectName: "doctorUndoAllButton"
                        Accessible.name: "Deshacer todas las reparaciones"
                        onClicked: root.undoAll()
                    }
                }
            }
        }
    }

    function setReport(fixed, failed, skipped, details) {
        root.fixedCount = fixed
        root.failedCount = failed
        root.skippedCount = skipped
        root._details = details || []
    }
}
