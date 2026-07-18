import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Overview"
    objectName: "libraryDoctorOverview"
    focus: true
    id: root

    property var doc: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: qsTr("Resumen"); width: parent.width }

        HeroMaterial {
            width: parent.width; height: 100; radius: MichiTheme.radius.lg; showGlow: true
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                Text { text: qsTr("Diagnóstico de biblioteca"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                Text { text: qsTr("Analiza y repara problemas en tu colección musical."); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
            }
        }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                Column { spacing: MichiTheme.spacing.xs
                    Text { text: qsTr("Revisados"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: String(root.doc ? root.doc.totalChecked : 0); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                }
                Column { spacing: MichiTheme.spacing.xs
                    Text { text: qsTr("Problemas"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: String(root.doc ? root.doc.issueCount : 0); color: (root.doc && root.doc.issueCount > 0) ? MichiTheme.colors.warning : MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                }
                Column { spacing: MichiTheme.spacing.xs
                    Text { text: qsTr("Metadata"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: String(root.doc ? root.doc.missingMetadataCount : 0); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.sectionTitleSize }
                }
                Column { spacing: MichiTheme.spacing.xs
                    Text { text: qsTr("Archivos"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: String(root.doc ? root.doc.missingFileCount : 0); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.sectionTitleSize }
                }
                Column { spacing: MichiTheme.spacing.xs
                    Text { text: qsTr("OK"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: String(root.doc ? root.doc.healthyCount : 0); color: MichiTheme.colors.success; font.pixelSize: MichiTheme.typography.sectionTitleSize }
                }
            }
        }

        StatusBadge {
            text: root.doc ? "Estado: qsTr(" + root.doc.status : ")"
            kind: root.doc && root.doc.status === "done" ? "success" :
                  root.doc && root.doc.status === "scanning" ? "warning" :
                  root.doc && root.doc.status === "error" ? "error" : "info"
            visible: root.doc && root.doc.status !== "idle"
        }
    }
}
