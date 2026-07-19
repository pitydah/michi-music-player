import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "syncHistoryPlaceholderPage"
    pageTitle: qsTr("Historial de sincronizacion")
    featureState: "planned"
    description: qsTr("El historial mostrara un registro detallado de todas las sincronizaciones realizadas: fecha, dispositivo, pistas transferidas y estado de cada operacion.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
