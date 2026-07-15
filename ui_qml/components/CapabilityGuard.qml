import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import QtQuick.Controls as QQC2
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
>>>>>>> Stashed changes
import "../theme"
import "states"

Item {
    id: root

    property string capabilityName: ""
    property bool checking: false
    property bool available: false
    property bool degraded: false
    property bool deferredPhysical: false

    default property alias availableContent: availableHost.children
    property alias unavailableContent: unavailableHost.children
    property alias degradedContent: degradedHost.children
    property alias loadingContent: loadingHost.children
    property alias deferredPhysicalContent: deferredPhysicalHost.children

    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "CapabilityGuard_" + (capabilityName || "unknown")

    Accessible.role: Accessible.Grouping
    Accessible.name: capabilityName || "Guardia de capacidad"
    Accessible.description: {
        if (root.checking) return "Verificando disponibilidad de " + capabilityName
        if (root.available) return capabilityName + " disponible"
        if (root.deferredPhysical) return capabilityName + " requiere hardware físico"
        if (root.degraded) return capabilityName + " funciona con limitaciones"
        return capabilityName + " no disponible"
    }

    function checkCapability(bridge) {
        if (!bridge || typeof bridge.has !== "function") {
            root.checking = false
            root.available = false
            root.degraded = false
            root.deferredPhysical = false
            return
        }
        root.checking = true
        root.available = false
        root.degraded = false
        root.deferredPhysical = false

        var caps = bridge.capabilities || {}
        var state = caps[root.capabilityName]
        if (state === undefined) {
            var hasCap = bridge.has(root.capabilityName)
            state = hasCap ? "available" : "unavailable"
        }
        root.available = state === "available"
        root.degraded = state === "degraded"
        root.deferredPhysical = state === "deferred_physical"
        root.checking = false
    }

    Item {
        id: availableHost
        anchors.fill: parent
<<<<<<< Updated upstream
=======
        visible: children.length > 0 && root.state === CapabilityGuard.AVAILABLE && root.availableContent === null
=======
import QtQuick.Controls as QQC2
import "../theme"
import "states"

Item {
    id: root

    property string capabilityName: ""
    property bool checking: false
    property bool available: false
    property bool degraded: false
    property bool deferredPhysical: false

    default property alias availableContent: availableHost.children
    property alias unavailableContent: unavailableHost.children
    property alias degradedContent: degradedHost.children
    property alias loadingContent: loadingHost.children
    property alias deferredPhysicalContent: deferredPhysicalHost.children

    signal primaryActionRequested()
    signal secondaryActionRequested()

    objectName: "CapabilityGuard_" + (capabilityName || "unknown")

    Accessible.role: Accessible.Grouping
    Accessible.name: capabilityName || "Guardia de capacidad"
    Accessible.description: {
        if (root.checking) return "Verificando disponibilidad de " + capabilityName
        if (root.available) return capabilityName + " disponible"
        if (root.deferredPhysical) return capabilityName + " requiere hardware físico"
        if (root.degraded) return capabilityName + " funciona con limitaciones"
        return capabilityName + " no disponible"
    }

    function checkCapability(bridge) {
        if (!bridge || typeof bridge.has !== "function") {
            root.checking = false
            root.available = false
            root.degraded = false
            root.deferredPhysical = false
            return
        }
        root.checking = true
        root.available = false
        root.degraded = false
        root.deferredPhysical = false

        var caps = bridge.capabilities || {}
        var state = caps[root.capabilityName]
        if (state === undefined) {
            var hasCap = bridge.has(root.capabilityName)
            state = hasCap ? "available" : "unavailable"
        }
        root.available = state === "available"
        root.degraded = state === "degraded"
        root.deferredPhysical = state === "deferred_physical"
        root.checking = false
    }

    Item {
        id: availableHost
        anchors.fill: parent
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        visible: root.available && !root.degraded && !root.checking && !root.deferredPhysical
    }

    Item {
        id: degradedHost
        anchors.fill: parent
        visible: root.degraded && !root.checking && !root.available && !root.deferredPhysical
        z: 5

        UnavailableState {
            anchors.centerIn: parent
            width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
            title: root.capabilityName + " con limitaciones"
            message: "Algunas funciones de " + root.capabilityName + " no están disponibles."
            iconText: "\u26A0"
        }
    }

    Item {
        id: deferredPhysicalHost
        anchors.fill: parent
        visible: root.deferredPhysical && !root.checking && !root.available && !root.degraded
        z: 5

        UnavailableState {
            anchors.centerIn: parent
            width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
            title: root.capabilityName + " requiere hardware"
            message: "Esta función necesita hardware físico especializado."
            iconText: "\u2699"
        }
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
        visible: !root.available && !root.degraded && !root.checking && !root.deferredPhysical

        UnavailableState {
            anchors.centerIn: parent
            width: Math.min(implicitWidth + MichiTheme.spacing.xl * 2, parent.width * 0.85)
            title: root.capabilityName + " no disponible"
            message: "Esta funcionalidad requiere servicios adicionales que no están activos."
            iconText: "\u26A0"
        }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
}
