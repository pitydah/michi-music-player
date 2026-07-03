import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null

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
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Audio Lab"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Herramientas de análisis, conversión y diagnóstico para tu biblioteca musical."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 80
                title: "Inspector de metadatos"
                subtitle: "Revisa campos, carátulas y consistencia de una pista."
                variant: "accent"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("metadata_inspector")
                }
            }

            SectionHeader { text: "Estado de la biblioteca"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.totalTracks : "—"; color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Canciones"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.missingMetadata : "—"; color: root.alab && root.alab.missingMetadata > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Sin metadata"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.missingCovers : "—"; color: root.alab && root.alab.missingCovers > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: "Sin carátula"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                }
            }

            SectionHeader { text: "Herramientas"; width: parent.width }

            Grid {
                width: parent.width; columns: 2; columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.alab ? root.alab.modules : []

                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                        title: modelData.title || ""
                        subtitle: modelData.desc || ""
                        variant: modelData.status === "available" ? "base" : "status"
                        onClicked: {
                            if (modelData.id === "diagnostics" && typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("audio_lab")
                        }
                    }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Solo lectura"; kind: "info" }
                    StatusBadge { text: "Interfaz clásica disponible"; kind: "disconnected" }
                }
            }
        }
    }
}
