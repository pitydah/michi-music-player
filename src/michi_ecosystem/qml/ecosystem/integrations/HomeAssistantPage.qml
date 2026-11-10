import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    signal navigationRequested(string routeId)
    onBackRequested: root.navigationRequested("ecosystem")
    property var integration: ({})
    property var integrationBridge: typeof homeAssistant !== "undefined" ? homeAssistant : null
    readonly property var bridgeConfig: integrationBridge ? integrationBridge.configuration : ({})

    eyebrow: qsTr("INTEGRACIÓN LOCAL")
    title: qsTr("Home Assistant")
    subtitle: qsTr("Expone control limitado mediante MQTT Discovery sin ceder autoridad de Michi Home.")
    iconName: "home"
    statusText: integrationBridge && integrationBridge.busy ? qsTr("Procesando…")
        : integrationBridge ? integrationBridge.connectionText : qsTr("Desactivado")
    statusTone: integrationBridge && integrationBridge.busy ? "active"
        : integrationBridge ? integrationBridge.connectionTone : "neutral"

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        RowLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.lg
            ColumnLayout {
                Layout.fillWidth: true
                MichiText { text: qsTr("Home Assistant"); role: "section" }
                MichiText {
                    text: qsTr("Desactivado por defecto. Michi sigue funcionando si Home Assistant o MQTT no están disponibles.")
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
            }
            MichiSwitch {
                checked: integrationBridge ? integrationBridge.enabled : false
                enabled: integrationBridge ? integrationBridge.available && !integrationBridge.busy : false
                text: qsTr("Activar Home Assistant")
                onToggled: if (integrationBridge) integrationBridge.setEnabled(checked)
            }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout2.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout2
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("MQTT"); role: "section" }
            MichiText {
                visible: text.length > 0
                text: integrationBridge ? integrationBridge.connectionDetail : ""
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                visible: !(integrationBridge && integrationBridge.configurable)
                text: qsTr("La conexión MQTT la configura el host. Ecosystem nunca lee ni muestra la contraseña guardada.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }

            GridLayout {
                visible: integrationBridge && integrationBridge.configurable
                Layout.fillWidth: true
                columns: root.compact ? 1 : 2
                columnSpacing: MichiSpacing.lg
                rowSpacing: MichiSpacing.md

                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText { text: qsTr("Broker"); role: "technical" }
                    MichiTextField {
                        id: brokerField
                        Layout.fillWidth: true
                        accessibleName: qsTr("Broker MQTT")
                        placeholderText: qsTr("mqtt.local")
                        text: root.bridgeConfig.broker ?? ""
                        enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText { text: qsTr("Puerto"); role: "technical" }
                    MichiTextField {
                        id: portField
                        Layout.fillWidth: true
                        accessibleName: qsTr("Puerto MQTT")
                        text: String(root.bridgeConfig.port ?? 1883)
                        validator: IntValidator { bottom: 1; top: 65535 }
                        enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText { text: qsTr("Usuario"); role: "technical" }
                    MichiTextField {
                        id: usernameField
                        Layout.fillWidth: true
                        accessibleName: qsTr("Usuario MQTT")
                        text: root.bridgeConfig.username ?? ""
                        enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    MichiText { text: qsTr("Contraseña"); role: "technical" }
                    MichiTextField {
                        id: passwordField
                        Layout.fillWidth: true
                        accessibleName: qsTr("Contraseña MQTT")
                        placeholderText: qsTr("Sin cambios si queda vacía")
                        echoMode: TextInput.Password
                        enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                    }
                }
            }

            Flow {
                visible: integrationBridge && integrationBridge.configurable
                Layout.fillWidth: true
                spacing: MichiSpacing.lg
                MichiSwitch {
                    id: tlsSwitch
                    text: qsTr("TLS")
                    checked: root.bridgeConfig.tls ?? false
                    enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                }
                MichiSwitch {
                    id: discoverySwitch
                    text: qsTr("Auto-discovery")
                    checked: root.bridgeConfig.autoDiscovery !== false
                    enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                }
                MichiSwitch {
                    id: devicesSwitch
                    text: qsTr("Publicar dispositivos")
                    checked: root.bridgeConfig.publishDevices !== false
                    enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                }
                MichiSwitch {
                    id: diagnosticsSwitch
                    text: qsTr("Diagnóstico")
                    checked: root.bridgeConfig.diagnostics !== false
                    enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                }
            }

            RowLayout {
                Layout.fillWidth: true
                MichiText {
                    Layout.fillWidth: true
                    text: qsTr("La contraseña es write-only: no vuelve desde el backend a esta pantalla.")
                    role: "secondary"
                    wrapMode: Text.WordWrap
                    visible: integrationBridge && integrationBridge.configurable
                }
                MichiButton {
                    visible: integrationBridge && integrationBridge.configurable
                    text: qsTr("Guardar MQTT")
                    variant: "primary"
                    enabled: integrationBridge && !integrationBridge.enabled && !integrationBridge.busy
                        && brokerField.text.trim().length > 0 && portField.acceptableInput
                    onClicked: {
                        integrationBridge.saveConfiguration(
                            brokerField.text,
                            Number(portField.text),
                            tlsSwitch.checked,
                            usernameField.text,
                            passwordField.text,
                            discoverySwitch.checked,
                            devicesSwitch.checked,
                            diagnosticsSwitch.checked)
                        passwordField.text = ""
                    }
                }
            }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout3.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout3
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Estado y recuperación"); role: "section" }
            EcosystemStatusRow {
                label: qsTr("Broker MQTT")
                status: (root.bridgeConfig.broker ?? integration.broker ?? "").length > 0
                    ? (root.bridgeConfig.broker ?? integration.broker) : qsTr("Sin configurar")
            }
            EcosystemStatusRow {
                label: qsTr("TLS")
                status: (root.bridgeConfig.tls ?? integration.tls) ? qsTr("Activado") : qsTr("Desactivado")
            }
            EcosystemStatusRow {
                label: qsTr("Auto-discovery")
                status: (root.bridgeConfig.autoDiscovery ?? integration.autoDiscovery) === false
                    ? qsTr("Desactivado") : qsTr("Activado")
            }
            MichiText {
                visible: integrationBridge && integrationBridge.errorMessage.length > 0
                text: integrationBridge ? integrationBridge.errorMessage : ""
                role: "secondary"
                color: MichiPalette.error
                wrapMode: Text.WordWrap
            }
            MichiButton {
                text: qsTr("Republicar discovery y estado")
                variant: "ghost"
                enabled: integrationBridge ? integrationBridge.enabled && !integrationBridge.busy : false
                onClicked: if (integrationBridge) integrationBridge.republish()
            }
        }
    }
}
