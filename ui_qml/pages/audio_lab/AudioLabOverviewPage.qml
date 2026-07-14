import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    Component.onCompleted: {
        if (root.alab && typeof root.alab.refresh !== "undefined")
            root.alab.refresh()
    }

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

            HeroMaterial {
                width: parent.width; height: 150; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Audio Lab"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Análisis técnico, conversión, normalización, integridad y comparación de archivos de audio."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.75; wrapMode: Text.WordWrap
                    }
                }
            }

            SelectionSummary { id: selectionSummary }

            SectionHeader { text: "Herramientas"; width: parent.width }

            Grid {
                width: parent.width; columns: 2; columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Análisis técnico"
                    subtitle: "Formato, codec, bitrate, calidad"
                    variant: "accent"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_analysis") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Conversión"
                    subtitle: "FLAC, MP3, AAC, Opus, WAV"
                    variant: "accent"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_conversion") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Normalización"
                    subtitle: "Loudness, pico, ganancia"
                    variant: "base"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_normalization") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "ReplayGain"
                    subtitle: "Etiquetas de ganancia"
                    variant: "base"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_replaygain") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Integridad"
                    subtitle: "Cabeceras, corrupción, checksum"
                    variant: "status"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_integrity") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Comparación"
                    subtitle: "Diferencias entre variantes"
                    variant: "status"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_comparison") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Trabajos"
                    subtitle: "Cola y estado de procesos"
                    variant: "base"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_jobs") }
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                    title: "Perfiles"
                    subtitle: "Presets de conversión"
                    variant: "base"
                    onClicked: { if (root.nav) root.nav.navigate("audio_lab_profiles") }
                }
            }

            SectionHeader { text: "Estado del backend"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text { text: "Backend: " + (root.alab ? (root.alab.backendInfo ? root.alab.backendInfo.backend : "no disponible") : "no disponible"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                    Text { text: "Pipeline: " + (root.alab ? (root.alab.pipelineInfo ? JSON.stringify(root.alab.pipelineInfo) : "") : ""); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                    StatusBadge { text: "Requiere ffmpeg para conversión"; kind: "info" }
                }
            }
        }
    }
}
