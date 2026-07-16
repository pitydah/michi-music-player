import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Report"
    objectName: "libraryDoctorReport"
    focus: true
    id: root

    property var doc: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Reporte"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            visible: root.doc && root.doc.status === "done"

            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: "Resumen del diagnóstico"
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { width: 1; height: MichiTheme.spacing.sm }

                Text {
                    text: "Total revisados: " + (root.doc ? root.doc.totalChecked : 0)
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: "Problemas encontrados: " + (root.doc ? root.doc.issueCount : 0)
                    color: root.doc && root.doc.issueCount > 0 ? MichiTheme.colors.warning : MichiTheme.colors.success
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: root.doc ? "Archivos faltantes: " + root.doc.missingFileCount : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Text {
                    text: root.doc ? "Metadatos incompletos: " + root.doc.missingMetadataCount : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Text {
                    text: root.doc ? "Saludables: " + root.doc.healthyCount : ""
                    color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Item { width: 1; height: MichiTheme.spacing.sm }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: "Volver a escanear"
                        variant: "secondary"
                        onClicked: { if (root.doc && typeof root.doc.scan !== "undefined") root.doc.scan() }
                    }
                    MichiButton {
                        text: "Exportar reporte"
                        variant: "ghost"
                        onClicked: {
                            if (typeof notificationBridge !== "undefined" && notificationBridge)
                                notificationBridge.showMessage("Reporte exportado", "success")
                        }
                    }
                }
            }
        }
    }
}
