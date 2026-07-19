import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "jellyfinPlaceholderPage"
    pageTitle: qsTr("Jellyfin")
    state: "planned"
    description: qsTr("La integracion con servidores Jellyfin via Subsonic API estara disponible en una proxima actualizacion. Accede a tu coleccion multimedia gestionada con Jellyfin.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
