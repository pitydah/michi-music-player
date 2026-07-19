import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioProcessingHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Procesamiento de audio"

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: qsTr("Procesamiento")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Ecualizacion, DSP, normalizacion y conversion de formatos.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
            }

            SectionHeader {
                text: qsTr("Herramientas")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: parent.width > 900 ? 3 : 2
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Ecualizador")
                    subtitle: qsTr("Ecualizador grafico y parametrico.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.processing")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Perfiles DSP")
                    subtitle: qsTr("Cadenas de procesamiento digital de senal.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.output_profiles")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Perfiles de salida")
                    subtitle: qsTr("Configuracion de DAC y dispositivos de salida.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.output_profiles")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Normalizacion")
                    subtitle: qsTr("Normalizacion de volumen por lote.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.normalization")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Conversion")
                    subtitle: qsTr("Conversion entre formatos de audio.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.conversion")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("ReplayGain")
                    subtitle: qsTr("Analisis y aplicacion de ReplayGain.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.replaygain")
                    }
                }

                GlassCard {
                    width: parent.width / parent.columns - MichiTheme.spacing.md * (parent.columns - 1) / parent.columns
                    height: 100
                    title: qsTr("Trabajos por lote")
                    subtitle: qsTr("Procesamiento batch programado.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("audio_lab.jobs")
                    }
                }
            }
        }
    }
}
