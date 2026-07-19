import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "portablePlayersPlaceholderPage"
    pageTitle: qsTr("Reproductores portatiles")
    featureState: "planned"
    description: qsTr("La sincronizacion con reproductores portatiles (DAPs) estara disponible en una proxima actualizacion. Podras transferir tu musica a dispositivos compatibles con almacenamiento USB o MTP.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
