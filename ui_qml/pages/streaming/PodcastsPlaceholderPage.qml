import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "podcastsPlaceholderPage"
    pageTitle: qsTr("Podcasts")
    state: "planned"
    description: qsTr("La interfaz esta disponible, pero el gestor de suscripciones y descargas todavia no esta habilitado en esta instalacion.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: "../../icons/sidebar/podcasts.svg"

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
