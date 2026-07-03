import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var smartTaggingBridge: typeof smartTaggingBridge !== "undefined" ? smartTaggingBridge : null

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
                text: "Smart Tagging"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Etiquetado inteligente"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Sugerencias automáticas de metadatos para tu biblioteca."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 70
                title: "Analizar archivo"
                subtitle: "Selecciona una canción desde Biblioteca para analizar"
                variant: "base"
            }

            SectionHeader { text: "Sugerencias"; width: parent.width }

            Repeater {
                model: root.smartTaggingBridge ? root.smartTaggingBridge.suggestions : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text {
                            width: parent.width * 0.25; text: modelData.field || ""
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30; text: modelData.current || "—"
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.30; text: "→ " + (modelData.suggested || "")
                            color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Text {
                text: "No hay sugerencias. Escanea un archivo para comenzar."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: root.smartTaggingBridge && root.smartTaggingBridge.suggestions.length === 0
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
