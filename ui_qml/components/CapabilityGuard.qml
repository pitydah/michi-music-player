import QtQuick
import QtQuick.Controls as QQC2
import "../theme"
import "states"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Capability Guard"
    objectName: "capabilityGuard"
    focus: true
    id: root

    property string capabilityName: ""
    property bool checking: false
    property bool available: false
    property bool degraded: false

    default property alias availableContent: availableHost.children
    property alias unavailableContent: unavailableHost.children
    property alias degradedContent: degradedHost.children
    property alias loadingContent: loadingHost.children

    signal primaryActionRequested()
    signal secondaryActionRequested()


    Accessible.description: {
        if (root.checking) return "Verificando disponibilidad de " + capabilityName
        if (root.available) return capabilityName + " disponible"
        if (root.degraded) return capabilityName + " funciona con limitaciones"
        return capabilityName + " no disponible"
    }

    function checkCapability(bridge) {
        if (!bridge || typeof bridge.has !== "function") {
            root.checking = false
            root.available = false
            root.degraded = false
            return
        }
        root.checking = true
        root.available = false
        root.degraded = false

        var caps = bridge.capabilities || {}
        var hasCap = bridge.has(root.capabilityName) || caps[root.capabilityName] === true
        root.available = hasCap
        root.degraded = false
        root.checking = false
    }

    Item {
        id: availableHost
        anchors.fill: parent
        visible: root.available && !root.degraded && !root.checking
    }

    Item {
        id: degradedHost
        anchors.fill: parent
        visible: root.degraded && !root.checking && !root.available
        z: 5
    }

    Item {
        id: loadingHost
        anchors.fill: parent
        visible: root.checking

        Loader {
            anchors.centerIn: parent
            active: root.checking
            sourceComponent: Component {
                LoadingState {
                    title: "Verificando disponibilidad"
                    message: "Comprobando " + root.capabilityName + "..."
                }
            }
        }
    }

    Item {
        id: unavailableHost
        anchors.fill: parent
        visible: !root.available && !root.degraded && !root.checking

        UnavailableState {
            anchors.centerIn: parent
            width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
            title: root.capabilityName + " no disponible"
            message: "Esta funcionalidad requiere servicios adicionales que no están activos."
            iconText: "\u26A0"
        }
    }
}
