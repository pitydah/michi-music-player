import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Home Assistant — integration requiring configuration.
 * The connector is not active in this installation, so the form and the
 * connection test stay disabled. The state legend explains the four
 * integration states the UI will distinguish once it exists.
 */
IntegrationPreviewPage {
    id: root
    objectName: "homeAssistantPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Home Assistant")

    featureTitle: qsTr("Home Assistant")
    featureDescription: qsTr("Conecta Michi con Home Assistant para descubrir entidades de audio (media_player), reflejar el estado de reproducción y participar en automatizaciones del hogar.")
    featureIcon: "home_assistant"
    featureState: "configuration_required"
    statusLabel: qsTr("Configuración requerida")
    statusKind: "warning"
    primaryActionText: qsTr("Abrir ajustes")
    secondaryActionText: qsTr("Volver a Conexiones")

    configTitle: qsTr("Conexión con Home Assistant")
    configDescription: qsTr("Se conectará con la URL de tu instancia y un token de acceso de larga duración creado en tu perfil de Home Assistant.")
    configHint: qsTr("Formulario deshabilitado: sin conector activo no hay dónde guardar ni validar estos datos.")

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
            label: qsTr("URL de la instancia")
            placeholderText: qsTr("http://homeassistant.local:8123")
            helperText: qsTr("Se habilitará cuando exista el conector.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        },
        MichiTextField {
            width: parent.width
            label: qsTr("Token de acceso")
            placeholderText: qsTr("••••••••••••••••")
            helperText: qsTr("Token de larga duración: Perfil → Seguridad → Tokens.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        },
        MichiButton {
            text: qsTr("Probar conexión")
            variant: "secondary"
            tooltipText: qsTr("Disponible cuando el conector esté implementado y el formulario habilitado.")
            enabled: false
            opacity: MichiTheme.opacity.disabled
        }
    ]

    SectionHeader { text: qsTr("Estados que distinguirá la integración") }

    GlassMaterial {
        width: root.contentWidth
        height: statesLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: statesLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    { label: qsTr("Disponible"), kind: "success", text: qsTr("Conector activo y conexión verificada con la instancia.") },
                    { label: qsTr("Configurada"), kind: "info", text: qsTr("Credenciales guardadas; falta la primera verificación.") },
                    { label: qsTr("No configurada"), kind: "warning", text: qsTr("Sin URL ni token: la integración no puede iniciarse.") },
                    { label: qsTr("Fallida"), kind: "error", text: qsTr("La última verificación falló; se mostrará el motivo y cómo resolverlo.") }
                ]

                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md

                    StatusBadge {
                        Layout.alignment: Qt.AlignTop
                        text: modelData.label
                        kind: modelData.kind
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

    SectionHeader { text: qsTr("Detección de entidades de audio (conceptual)") }

    GlassMaterial {
        width: root.contentWidth
        height: entitiesLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: entitiesLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                Layout.fillWidth: true
                text: qsTr("Cuando la conexión exista, Michi detectará entidades media_player expuestas por Home Assistant: altavoces, receptores y zonas con control de volumen y fuente. Esta lista está vacía a propósito: no hay conector activo ni entidades detectadas.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }

    GlassMaterial {
        width: root.contentWidth
        height: currentLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "accent"
        radius: MichiTheme.radius.md

        RowLayout {
            id: currentLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            StatusBadge {
                Layout.alignment: Qt.AlignTop
                text: qsTr("No configurada")
                kind: "warning"
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Estado actual en esta instalación: no configurada. No hay credenciales guardadas, ni conexión activa, ni entidades detectadas.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }
}
