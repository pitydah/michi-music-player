import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Navidrome — planned integration preview.
 * Navidrome speaks the Subsonic API; the connector is not implemented,
 * so the configuration form is a disabled, non-persistent preview.
 */
IntegrationPreviewPage {
    id: root
    objectName: "navidromePage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Navidrome")

    featureTitle: qsTr("Navidrome")
    featureDescription: qsTr("Conecta Michi con tu servidor Navidrome a través de la API compatible con Subsonic: tu biblioteca remota aparecerá como una fuente más, con búsqueda, carátulas y streaming.")
    featureIcon: "navidrome"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Revisar requisitos")
    secondaryActionText: qsTr("Volver a Conexiones")

    configTitle: qsTr("Conexión al servidor")
    configDescription: qsTr("Navidrome expone la API Subsonic. Cuando el conector exista, bastarán la URL del servidor y tus credenciales.")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
    onSecondaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("connections")
    }

    formContent: [
        MichiTextField {
            width: parent.width
            label: qsTr("URL del servidor")
            placeholderText: qsTr("https://navidrome.example.com")
            helperText: qsTr("Se habilitará cuando exista el conector Subsonic.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        },
        MichiTextField {
            width: parent.width
            label: qsTr("Usuario")
            placeholderText: qsTr("usuario")
            helperText: qsTr("Las credenciales se validarán contra el servidor al guardar.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        }
    ]

    SectionHeader { text: qsTr("Qué aportará la integración") }

    GlassMaterial {
        width: root.contentWidth
        height: benefitsLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: benefitsLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    { icon: "library", text: qsTr("Tu biblioteca remota como fuente local: artistas, álbumes y pistas servidos por Navidrome.") },
                    { icon: "search", text: qsTr("Búsqueda unificada: resultados locales y remotos en la misma vista.") },
                    { icon: "streaming", text: qsTr("Streaming bajo demanda sin duplicar archivos en este equipo.") }
                ]

                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md

                    MichiIcon {
                        Layout.alignment: Qt.AlignTop
                        iconKey: modelData.icon
                        size: MichiTheme.iconSizeRegular
                        color: MichiTheme.colors.accentPrimary
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.text
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.secondarySize
                        wrapMode: Text.WordWrap
                        lineHeight: MichiTheme.typography.lineHeightBody
                    }
                }
            }
        }
    }

    GlassMaterial {
        width: root.contentWidth
        height: noteLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "accent"
        radius: MichiTheme.radius.md

        Text {
            id: noteLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            text: qsTr("Estado real: el conector Subsonic/Navidrome no está implementado en esta instalación. No hay conexión, caché remota ni credenciales guardadas.")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.secondarySize
            wrapMode: Text.WordWrap
            lineHeight: MichiTheme.typography.lineHeightBody
        }
    }
}
