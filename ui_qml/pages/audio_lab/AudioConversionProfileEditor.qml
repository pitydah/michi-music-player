import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

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
                text: "Perfiles de conversión"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Portable MP3, Portable AAC, Efficient Opus, Lossless FLAC, Archival FLAC, PCM WAV, Hi-Res Preserve, Device Compatible, Custom"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            Repeater {
                model: [
                    { name: "Portable MP3", format: "MP3", bitrate: "320k", sr: "44100", depth: "16" },
                    { name: "Portable AAC", format: "AAC", bitrate: "256k", sr: "44100", depth: "16" },
                    { name: "Efficient Opus", format: "Opus", bitrate: "128k", sr: "48000", depth: "16" },
                    { name: "Lossless FLAC", format: "FLAC", bitrate: "—", sr: "44100", depth: "16" },
                    { name: "Archival FLAC", format: "FLAC", bitrate: "—", sr: "192000", depth: "24" },
                    { name: "PCM WAV", format: "WAV", bitrate: "—", sr: "44100", depth: "16" },
                    { name: "Hi-Res Preserve", format: "FLAC", bitrate: "—", sr: "Original", depth: "Original" },
                    { name: "Device Compatible", format: "MP3", bitrate: "192k", sr: "44100", depth: "16" },
                    { name: "Custom", format: "FLAC", bitrate: "—", sr: "Original", depth: "Original" },
                ]

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radiusSm; variant: "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.20; text: modelData.name; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.12; text: modelData.format; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.12; text: modelData.bitrate; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.15; text: modelData.sr + " Hz"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.10; text: modelData.depth + " bit"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        MichiButton { width: 60; height: 28; text: "Usar"; variant: "primary"; anchors.verticalCenter: parent.verticalCenter; onClicked: { } }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Guardar custom"; variant: "secondary"; enabled: false }
                MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
            }
        }
    }
}
