import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi Music Stream")
    objectName: "michiMusicStreamPanel"
    focus: true
    id: root

    property string streamState: "concept"
    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    implicitHeight: responsive.compact ? 720 : 420

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        if (root.bridge && root.bridge.streamState !== undefined)
            root.streamState = root.bridge.streamState
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg

        GlassMaterial {
            width: parent.width
            height: responsive.compact ? 144 : 104
            variant: "base"
            radius: MichiTheme.radius.md

            GridLayout {
                anchors.fill: parent
                anchors.margins: responsive.compact
                                 ? MichiTheme.spacing.md
                                 : MichiTheme.spacing.lg
                columns: responsive.compact ? 1 : 2
                columnSpacing: MichiTheme.spacing.lg
                rowSpacing: MichiTheme.spacing.sm

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    spacing: MichiTheme.spacing.xs

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Michi Music Stream")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Sistema propio del ecosistema Michi para transmitir música a receptores y equipos de audio dentro de la red local.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                    }
                }

                StatusBadge {
                    Layout.alignment: responsive.compact ? Qt.AlignLeft : Qt.AlignVCenter
                    text: qsTr("Concepto")
                    kind: "experimental"
                }
            }
        }

        Text {
            text: qsTr("Componentes del sistema")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.sectionTitleSize
            font.weight: MichiTheme.typography.weightSemiBold
        }

        Grid {
            width: parent.width
            columns: responsive.columnCount
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.md

            Repeater {
                model: [
                    { title: qsTr("Receptores Michi"), desc: qsTr("Dispositivos de audio en red") },
                    { title: qsTr("Salas y zonas"), desc: qsTr("Agrupación de receptores") },
                    { title: qsTr("Transmisión local"), desc: qsTr("Streaming sin servidor externo") },
                    { title: qsTr("Sincronización multiroom"), desc: qsTr("Audio sincronizado en todas las salas") },
                    { title: qsTr("Diagnóstico de latencia"), desc: qsTr("Medición de delay en la red") },
                    { title: qsTr("Protocolo Michi Stream"), desc: qsTr("Capa de transporte del ecosistema") }
                ]

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1))
                           / parent.columns
                    height: 80
                    title: modelData.title
                    subtitle: modelData.desc
                    variant: "base"
                }
            }
        }
    }
}
