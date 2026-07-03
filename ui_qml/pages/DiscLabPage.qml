import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

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
                text: "Disc Lab"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 160; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text { text: "Laboratorio de discos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                    Text { text: "Detección, análisis y ripping de CD/DVD."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Escanear disco"
                subtitle: "Detecta la unidad y analiza el contenido"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Estado del ripping"
                subtitle: "Sin trabajos activos"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Perfil de ripping"
                subtitle: "Formato: FLAC, Calidad: CD (16/44.1)"
                variant: "base"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
                    StatusBadge { text: "Experimental — Sin unidad detectada"; kind: "experimental" }
                }
            }
        }
    }
}
