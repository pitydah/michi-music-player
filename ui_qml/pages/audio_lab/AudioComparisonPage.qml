import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
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
                text: "Comparación de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Compara variantes por: format, codec, bitrate, sample rate, bit depth, channels, size, loudness, peak, metadata, waveform summary, hash, integrity. No afirmamos 'suena mejor' por heurística."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            SectionHeader { text: "Archivo A"; width: parent.width }
            AudioInputSelection {}

            SectionHeader { text: "Archivo B"; width: parent.width }
            AudioInputSelection {}

            SectionHeader { text: "Dimensiones de comparación"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Repeater {
                        model: ["Formato", "Codec", "Bitrate", "Sample Rate", "Bit Depth", "Canales", "Tamaño", "Loudness", "Peak", "Metadata", "Hash", "Integridad"]
                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: modelData; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: 120 }
                            Text { text: "—"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 100 }
                            Text { text: "vs"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 30 }
                            Text { text: "—"; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 100 }
                            Text { text: ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Comparar"; variant: "primary" }
                MichiButton { text: "Intercambiar A/B"; variant: "secondary" }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona dos archivos para comparar"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 60
            }
        }
    }
}
