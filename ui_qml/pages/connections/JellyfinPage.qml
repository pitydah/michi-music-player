import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Jellyfin — planned integration preview, music libraries only.
 * Video libraries are explicitly out of scope for this integration.
 */
IntegrationPreviewPage {
    id: root
    objectName: "jellyfinPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Jellyfin")

    featureTitle: qsTr("Jellyfin")
    featureDescription: qsTr("Integración con tus bibliotecas de música de Jellyfin: artistas, álbumes y listas de reproducción servidos desde tu servidor hacia Michi.")
    featureIcon: "jellyfin"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Revisar requisitos")
    secondaryActionText: qsTr("Volver a Conexiones")

    configTitle: qsTr("Conexión al servidor")
    configDescription: qsTr("Jellyfin se conectará con la URL del servidor y un token de API generado desde su panel de administración.")

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
            placeholderText: qsTr("https://jellyfin.example.com")
            helperText: qsTr("Se habilitará cuando exista el conector Jellyfin.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        },
        MichiTextField {
            width: parent.width
            label: qsTr("Token de API")
            placeholderText: qsTr("••••••••••••••••")
            helperText: qsTr("Se genera en Jellyfin: Panel → Avanzado → Claves de API.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        }
    ]

    SectionHeader { text: qsTr("Alcance: solo música") }

    RowLayout {
        width: root.contentWidth
        spacing: MichiTheme.spacing.md

        Repeater {
            model: [
                { icon: "artists", title: qsTr("Artistas") },
                { icon: "albums", title: qsTr("Álbumes") },
                { icon: "playlists", title: qsTr("Listas") },
                { icon: "streaming", title: qsTr("Servidor remoto") }
            ]

            delegate: GlassMaterial {
                required property var modelData
                Layout.fillWidth: true
                Layout.minimumWidth: 140
                implicitHeight: scopeLayout.implicitHeight + MichiTheme.spacing.lg * 2
                variant: "status"
                radius: MichiTheme.radius.md

                ColumnLayout {
                    id: scopeLayout
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    MichiIcon {
                        iconKey: modelData.icon
                        size: MichiTheme.iconSizeLarge
                        color: MichiTheme.colors.accentPrimary
                        accessibleName: modelData.title
                    }

                    Text {
                        Layout.fillWidth: true
                        text: modelData.title
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        wrapMode: Text.WordWrap
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

        ColumnLayout {
            id: noteLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                Layout.fillWidth: true
                text: qsTr("Música sí, vídeo no")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("La integración se limitará a bibliotecas de música; el contenido de vídeo de Jellyfin está fuera del alcance. Estado real: el conector no está implementado y no hay servidor configurado.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }
}
