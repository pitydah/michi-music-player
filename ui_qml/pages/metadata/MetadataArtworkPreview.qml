import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Metadata Artwork Preview"
    objectName: "metadataArtworkPreview"
    focus: true
    id: root

    property string artworkStatus: ""
    property string coverKey: ""

    implicitHeight: 120

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.sm
        color: MichiTheme.colors.surfaceCard

        Row {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg

            CoverImage {
                width: 80
                height: 80
                coverRadius: MichiTheme.radius.xs
                coverKey: root.coverKey
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    text: "Carátula"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.artworkStatus || "Sin carátula"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }
}
