import QtQuick
import "../../theme"
import "../../components"

FeatureStatePage {
    id: root
    objectName: "adcRecorderPlaceholderPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Grabación ADC")

    pageTitle: qsTr("Grabación ADC")
    featureState: "experimental"
    iconSource: "../../../icons/sidebar/capture.svg"
    description: qsTr("Grabación desde fuentes analógicas (vinilo, casete, entrada de línea) mediante un conversor ADC. La interfaz dedicada de captura aún no está habilitada en esta instalación.")
    details: qsTr("La digitalización analógica permanece experimental hasta completar la validación con hardware real. La ecualización RIAA nunca se aplica de forma automática.")
    primaryActionText: qsTr("Volver a Captura")

    onPrimaryAction: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("audio_lab.capture")
    }
}
