import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var mb: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Vista previa"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: root.mb && root.mb.trackTitle ? "Título: " + root.mb.trackTitle : "Sin datos"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: root.mb && root.mb.trackArtist ? "Artista: " + root.mb.trackArtist : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Text {
                    text: root.mb && root.mb.trackAlbum ? "Álbum: " + root.mb.trackAlbum : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Text {
                    text: root.mb ? root.mb.qualitySummary : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }
            }
        }
    }
}
