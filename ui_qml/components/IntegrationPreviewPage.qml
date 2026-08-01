import QtQuick
import QtQuick.Layouts
import "../theme"
import "."
import "../materials"

/* IntegrationPreviewPage — PlannedFeaturePage variant for external
 * integrations that will require configuration (Navidrome, Jellyfin,
 * Home Assistant, ...).
 *
 * Adds a disabled configuration form preview between the hero and the
 * page content. Fields are declared via `formContent`; every field must
 * stay disabled until a real connector contract exists. The form never
 * persists anything: it is an honest preview of the future configuration.
 */
PlannedFeaturePage {
    id: root
    objectName: "integrationPreviewPage"

    property string configTitle: qsTr("Vista previa de configuración")
    property string configDescription: ""
    property string configHint: qsTr("Los campos se habilitarán cuando exista el conector. Nada de lo que se muestra aquí se guarda ni se envía.")
    property alias formContent: formColumn.data
    default property alias content: extraColumn.data

    GlassMaterial {
        width: root.contentWidth
        height: configLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: configLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: root.configTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    text: root.configDescription
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.secondarySize
                    wrapMode: Text.WordWrap
                    lineHeight: MichiTheme.typography.lineHeightBody
                    visible: text !== ""
                }
            }

            Column {
                id: formColumn
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.md
            }

            Text {
                Layout.fillWidth: true
                text: root.configHint
                color: MichiTheme.colors.textTertiary
                font.pixelSize: MichiTheme.typography.captionSize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
                visible: text !== ""
            }
        }
    }

    Column {
        id: extraColumn
        width: root.contentWidth
        spacing: MichiTheme.spacing.md
    }
}
