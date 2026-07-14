import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var doc: null
    property var _selectedIssue: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Detalle del problema"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            visible: root._selectedIssue !== null
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: root._selectedIssue ? root._selectedIssue.type : ""
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root._selectedIssue ? root._selectedIssue.detail : ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap; width: parent.width
                }

                Text {
                    text: root._selectedIssue && root._selectedIssue.filepath ? "Archivo: " + root._selectedIssue.filepath : ""
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }
            }
        }
    }

    function showIssue(issue) {
        root._selectedIssue = issue
    }
}
