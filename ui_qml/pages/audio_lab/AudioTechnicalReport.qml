import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Technical Report"
    objectName: "audioTechnicalReport"
    focus: true
    id: root

    property var analysisResult: null

    visible: root.analysisResult !== null

    GlassMaterial {
        width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
            Text { text: "Reporte técnico"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
            Repeater {
                model: root.analysisResult ? Object.keys(root.analysisResult) : []
                Row {
                    spacing: MichiTheme.spacing.sm
                    Text { text: modelData + ": "; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: 140 }
                    Text { text: root.analysisResult ? String(root.analysisResult[modelData]) : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }
                }
            }
        }
    }
}
