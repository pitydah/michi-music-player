import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "syncPlansPlaceholderPage"
    pageTitle: qsTr("Planes de sincronizacion")
    featureState: "planned"
    description: qsTr("Los planes de sincronizacion permitiran programar transferencias automaticas segun reglas, generos, playlists y espacio disponible en el dispositivo destino.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
