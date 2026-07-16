import QtQuick
import QtQuick.Controls as QQC2
import "../theme"
import "states"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Capability Aware"
    objectName: "capabilityAwarePage"
    focus: true
    id: root

    property var capabilityBridge: null
    property var requiredCapabilities: []
    property bool allCapabilitiesAvailable: false
    property bool checkingCapabilities: true

    default property alias content: contentHost.children
    property alias unavailableContent: unavailableHost.children

    signal primaryActionRequested()
    signal retryRequested()


    Accessible.description: root.checkingCapabilities
        ? "Verificando capacidades requeridas"
        : root.allCapabilitiesAvailable
            ? "Todas las capacidades disponibles"
            : "Faltan capacidades requeridas"

    function checkCapabilities() {
        root.checkingCapabilities = true
        root.allCapabilitiesAvailable = false

        if (!root.capabilityBridge || typeof root.capabilityBridge.has !== "function") {
            root.checkingCapabilities = false
            root.allCapabilitiesAvailable = false
            return
        }

        var missing = []
        for (var i = 0; i < root.requiredCapabilities.length; i++) {
            var cap = root.requiredCapabilities[i]
            if (!root.capabilityBridge.has(cap)) {
                missing.push(cap)
            }
        }

        root.allCapabilitiesAvailable = missing.length === 0
        root.checkingCapabilities = false
    }

    onCapabilityBridgeChanged: root.checkCapabilities()
    onRequiredCapabilitiesChanged: root.checkCapabilities()

    Component.onCompleted: root.checkCapabilities()

    Item {
        id: contentHost
        anchors.fill: parent
        visible: root.allCapabilitiesAvailable && !root.checkingCapabilities
    }

    Item {
        id: checkingHost
        anchors.fill: parent
        visible: root.checkingCapabilities

        LoadingState {
            anchors.centerIn: parent
            title: "Verificando capacidades"
            message: "Comprobando servicios requeridos..."
        }
    }

    Item {
        id: unavailableHost
        anchors.fill: parent
        visible: !root.allCapabilitiesAvailable && !root.checkingCapabilities
    }

    Item {
        anchors.fill: parent
        visible: !root.allCapabilitiesAvailable && !root.checkingCapabilities

        UnavailableState {
            anchors.centerIn: parent
            width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
            title: "Funcionalidad no disponible"
            message: "Esta página requiere servicios que no están disponibles en este momento."
            details: root.requiredCapabilities.length > 0
                ? "Capacidades requeridas: " + root.requiredCapabilities.join(", ")
                : ""
            primaryActionText: "Reintentar"

            onPrimaryActionRequested: root.retryRequested()
        }
    }

    function retry() {
        root.checkCapabilities()
    }
}
