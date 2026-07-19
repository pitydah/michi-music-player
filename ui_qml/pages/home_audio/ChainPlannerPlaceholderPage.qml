import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "chainPlannerPlaceholderPage"
    pageTitle: qsTr("Planificador de cadenas")
    state: "planned"
    description: qsTr("Disena y configura tus cadenas de audio fisicas: DAC, amplificador, ecualizador, altavoces. Esta funcionalidad estara disponible en una proxima actualizacion.")
    primaryActionText: qsTr("Ver requisitos")
    iconSource: ""

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("settings")
    }
}
