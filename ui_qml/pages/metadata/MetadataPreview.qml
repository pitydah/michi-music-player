import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Preview"
    objectName: "metadataPreview"
    focus: true
    id: root

    property var mb: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: qsTr("Vista previa"); width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radius.md; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: root.mb && root.mb.trackTitle ? "Título: qsTr(" + root.mb.trackTitle : ")Sin datos"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: root.mb && root.mb.trackArtist ? "Artista: qsTr(" + root.mb.trackArtist : ")"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: text !== ""
                }

                Text {
                    text: root.mb && root.mb.trackAlbum ? "Álbum: qsTr(" + root.mb.trackAlbum : ")"
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
