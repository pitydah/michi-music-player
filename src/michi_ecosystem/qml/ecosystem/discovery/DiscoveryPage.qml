import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    objectName: "ecosystemDiscoveryPage"
    signal navigationRequested(string routeId)
    eyebrow: qsTr("RED LOCAL")
    title: qsTr("Descubrimiento")
    subtitle: qsTr("Observaciones actuales de dispositivos. La detección de red la realiza el servicio de discovery del host.")
    iconName: "search"
    onBackRequested: root.navigationRequested("ecosystem")

    MichiText {
        Layout.fillWidth: true
        text: qsTr("Los anuncios mDNS y Whisker no conceden confianza por sí solos. Michi Home determina la membresía.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.devices.length === 0
        text: qsTr("No hay dispositivos observados en este momento. Revisa la red local y el estado de Michi Link.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: ecosystemOperations.devices
        delegate: MichiGlassSurface {
            id: observedCard
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: observedContent.implicitHeight + 2 * contentPadding
            elevation: "subtle"
            ColumnLayout {
                id: observedContent
                anchors.fill: parent
                spacing: MichiSpacing.sm
                MichiText {
                    Layout.fillWidth: true
                    text: observedCard.modelData.name
                    role: "section"
                }
                MichiText {
                    Layout.fillWidth: true
                    text: observedCard.modelData.online ? qsTr("En línea") : qsTr("Sin presencia confirmada")
                    role: "secondary"
                }
                MichiText {
                    Layout.fillWidth: true
                    text: observedCard.modelData.trusted ? qsTr("Miembro activo de Michi Home") : qsTr("No incorporado a Michi Home")
                    role: "secondary"
                }
                MichiButton {
                    text: qsTr("Ver dispositivo")
                    variant: "ghost"
                    enabled: observedCard.modelData.detailAvailable && !ecosystemOperations.busy
                    onClicked: ecosystemOperations.openDevice(observedCard.modelData.id)
                }
            }
        }
    }
}
