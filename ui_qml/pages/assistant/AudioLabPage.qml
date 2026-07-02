import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiSpacing.xl
        contentHeight: column.height + MichiSpacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiSpacing.lg

            HeroMaterial {
                width: parent.width
                height: 140
                radius: 16
                showGlow: true

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.xl
                    spacing: MichiSpacing.sm

                    Text {
                        text: "Audio Lab"
                        color: MichiColors.textPrimary
                        font.pixelSize: MichiTypography.heroTitleSize
                        font.weight: MichiTypography.weightBold
                    }

                    Text {
                        text: "Herramientas de análisis, conversión y diagnóstico para tu biblioteca musical."
                        color: MichiColors.textSecondary
                        font.pixelSize: MichiTypography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: "Herramientas disponibles"
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: MichiSpacing.md
                rowSpacing: MichiSpacing.md

                Repeater {
                    model: [
                        { title: "Diagnóstico", desc: "Analiza la calidad de tus archivos de audio" },
                        { title: "Conversión", desc: "Convierte entre formatos de audio" },
                        { title: "Identificador", desc: "Reconoce canciones por su huella digital" },
                        { title: "Vinilo", desc: "Captura y digitaliza desde vinilo" },
                        { title: "Organizar", desc: "Renombra y organiza archivos" },
                        { title: "Letras", desc: "Busca y edita letras de canciones" },
                        { title: "Carátulas", desc: "Gestiona las imágenes de tus álbumes" },
                        { title: "MusicBrainz", desc: "Busca metadatos en MusicBrainz" },
                    ]

                    GlassCard {
                        width: (parent.width - MichiSpacing.md) / 2
                        height: 80
                        title: modelData.title
                        subtitle: modelData.desc
                        variant: "base"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("audio_lab")
                        }
                    }
                }
            }

            StatusBadge {
                text: "Interfaz clásica disponible"
                kind: "info"
            }
        }
    }
}
