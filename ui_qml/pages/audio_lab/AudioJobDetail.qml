import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var jobData: null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    visible: root.jobData !== null

    GlassMaterial {
        width: parent.width; radius: MichiTheme.radiusMd; variant: root.jobData && root.jobData.state === "failed" ? "danger" : "base"
        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
            Text { text: root.jobData ? root.jobData.title : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
            Text { text: "Estado: " + (root.jobData ? root.jobData.state : ""); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
            Text { text: "Progreso: " + (root.jobData && root.jobData.progress ? Math.round(root.jobData.progress * 100) + "%" : "0%"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: "Error: " + (root.jobData ? (root.jobData.error_code || "") : ""); color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; visible: root.jobData && root.jobData.state === "failed" }
            Row { spacing: MichiTheme.spacing.sm
                MichiButton { text: "Reintentar"; variant: "secondary"; enabled: root.jobData && root.jobData.state === "failed" }
                MichiButton { text: "Cancelar"; variant: "danger"; enabled: root.jobData && root.jobData.state === "running" }
                MichiButton { text: "Abrir output"; variant: "ghost" }
            }
        }
    }
}
