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
                text: "Library Doctor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 160; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Diagnóstico de biblioteca"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Analiza y repara problemas en tu colección musical."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Archivos sin metadata"
                subtitle: "Canciones que carecen de información básica"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Archivos duplicados"
                subtitle: "Canciones repetidas en la biblioteca"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Carátulas faltantes"
                subtitle: "Álbumes sin imagen de portada"
                variant: "base"
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Problemas de organización"
                subtitle: "Archivos mal nombrados o en ubicaciones incorrectas"
                variant: "base"
            }

            MichiButton {
                text: "Escanear biblioteca"
                variant: "primary"
                width: parent.width
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
