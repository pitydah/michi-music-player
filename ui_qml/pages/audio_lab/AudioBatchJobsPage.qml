import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var jobBr: typeof jobBridge !== "undefined" ? jobBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Trabajos de Audio Lab"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Queue, active, history, progress per file, global, speed, ETA, warnings, errors, retry, cancel, pause/resume, open output, add to library, play output, compare output."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.jobBr ? root.jobBr.activeCount : "0"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Activos"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.jobBr ? root.jobBr.jobs.length : "0"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Total"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                }
            }

            SectionHeader { text: "Trabajos activos"; width: parent.width }

            Repeater {
                model: root.jobBr ? root.jobBr.jobs : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: modelData.state === "failed" ? "danger" : modelData.state === "completed" ? "success" : "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.30; text: modelData.title || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.15; text: modelData.state || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.15; text: modelData.progress ? Math.round(modelData.progress * 100) + "%" : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        MichiButton { width: 50; height: 24; text: "Ver"; variant: "ghost"; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Limpiar completados"; variant: "secondary"; onClicked: { if (root.jobBr) root.jobBr.clearCompleted() } }
                MichiButton { text: "Limpiar fallidos"; variant: "danger"; onClicked: { if (root.jobBr) root.jobBr.clearFailed() } }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }
        }
    }
}
