import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "navidromePlaceholderPage"
    pageTitle: qsTr("Navidrome")
    featureState: "planned"
    description: qsTr("La integracion con servidores Navidrome via Subsonic API estara disponible en una proxima actualizacion. Podras explorar y reproducir tu musica directamente desde tu servidor Navidrome.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
