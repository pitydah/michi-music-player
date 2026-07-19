import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "bigServerPlaceholderPage"
    pageTitle: qsTr("Michi Big Server")
    featureState: "planned"
    description: qsTr("Michi Big Server permitira centralizar tu biblioteca musical y servirla a multiples clientes Michi en tu red local. El protocolo de comunicacion esta en fase de estabilizacion.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
