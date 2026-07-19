import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "homeAssistantPlaceholderPage"
    pageTitle: qsTr("Home Assistant")
    state: "configuration_required"
    description: qsTr("Conecta Michi con Home Assistant para automatizar tu experiencia musical. Configura la URL de tu instancia y el token de acceso para habilitar el control por voz y automatizaciones.")
    primaryActionText: qsTr("Configurar conexion")
    secondaryActionText: qsTr("Ver documentacion")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }

    onSecondaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
