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
                text: "Integridad de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Decode verification, invalid header, truncated stream, unreadable file, unsupported codec, duration mismatch, corrupted frames, checksum, duplicate content, metadata inconsistency, artwork corruption, file extension mismatch."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {}
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Acciones"; width: parent.width }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Verificar integridad"; variant: "primary" }
                MichiButton { text: "Verificación rápida"; variant: "secondary" }
                MichiButton { text: "Detectar duplicados"; variant: "secondary" }
            }

            SectionHeader { text: "Resultados"; width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Text {
                    anchors.centerIn: parent
                    text: "Selecciona archivos para verificar integridad"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
                height: 80
            }

            MichiButton { text: "Volver"; variant: "ghost"; onClicked: { if (root.nav) root.nav.back() } }
        }
    }
}
