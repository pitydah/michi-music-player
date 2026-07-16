import QtQuick
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi Music Stream"
    objectName: "michiMusicStreamPanel"
    focus: true
    id: root

    property string streamState: "concept"

    implicitHeight: 420

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg

        GlassMaterial {
            width: parent.width
            height: 80
            variant: "base"
            radius: MichiTheme.radiusMd

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.lg

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Michi Music Stream"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: "Sistema propio del ecosistema Michi para transmitir música a receptores y equipos de audio dentro de la red local."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width - 100
                        wrapMode: Text.WordWrap
                    }
                }

                StatusBadge { text: "Concepto"; kind: "experimental" }
            }
        }

        Text {
            text: "Componentes del sistema"
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Grid {
            width: parent.width
            columns: 2
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.md

            Repeater {
                model: [
                    { title: "Receptores Michi", desc: "Dispositivos de audio en red" },
                    { title: "Salas y zonas", desc: "Agrupación de receptores" },
                    { title: "Transmisión local", desc: "Streaming sin servidor externo" },
                    { title: "Sincronización multiroom", desc: "Audio sincronizado en todas las salas" },
                    { title: "Diagnóstico de latencia", desc: "Medición de delay en la red" },
                    { title: "Protocolo Michi Stream", desc: "Capa de transporte del ecosistema" }
                ]

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2
                    height: 80
                    title: modelData.title
                    subtitle: modelData.desc
                    variant: "base"
                }
            }
        }
    }
}
