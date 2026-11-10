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

    function discoveryStateLabel() {
        if (!ecosystemOperations.discoveryAvailable)
            return qsTr("Descubrimiento no disponible en este host")
        switch (ecosystemOperations.discoveryState) {
        case "searching":
            return qsTr("Búsqueda manual activa")
        case "expired":
            return qsTr("La búsqueda alcanzó el tiempo máximo y se detuvo")
        case "error":
            return qsTr("La búsqueda informó un error")
        default:
            return qsTr("Búsqueda detenida")
        }
    }

    MichiGlassSurface {
        Layout.fillWidth: true
        implicitHeight: discoveryControls.implicitHeight + 2 * contentPadding
        elevation: "subtle"
        ColumnLayout {
            id: discoveryControls
            anchors.fill: parent
            spacing: MichiSpacing.sm
            MichiText {
                Layout.fillWidth: true
                text: root.discoveryStateLabel()
                role: "section"
            }
            MichiText {
                Layout.fillWidth: true
                text: qsTr("La búsqueda sólo se ejecuta cuando la inicias. Puedes detenerla en cualquier momento.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            RowLayout {
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Buscar ahora")
                    enabled: ecosystemOperations.discoveryAvailable
                        && !ecosystemOperations.discoveryRunning
                    onClicked: ecosystemOperations.startDiscovery()
                }
                MichiButton {
                    text: qsTr("Detener búsqueda")
                    variant: "ghost"
                    enabled: ecosystemOperations.discoveryRunning
                    onClicked: ecosystemOperations.stopDiscovery()
                }
                Item { Layout.fillWidth: true }
            }
        }
    }

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
