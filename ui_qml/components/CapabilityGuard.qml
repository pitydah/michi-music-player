import QtQuick
import QtQuick.Controls
import "../theme"

FocusScope {
    id: root

    enum CapabilityState {
        AVAILABLE,
        UNAVAILABLE,
        DEGRADED,
        LOADING
    }

    property string capabilityName: ""
    property int state: CapabilityGuard.AVAILABLE
    property string unavailableReason: "No disponible"
    property string degradedReason: "Funcionamiento limitado"
    property string objectName: "capabilityGuard"

    property Component availableContent: null
    property Component unavailableContent: null
    property Component degradedContent: null
    property Component loadingContent: null

    default property alias content: fallback.children

    activeFocusOnTab: true

    Accessible.role: Accessible.Panel
    Accessible.name: root.capabilityName !== "" ? root.capabilityName : "Capacidad"
    Accessible.description: {
        switch (root.state) {
            case CapabilityGuard.UNAVAILABLE: return root.unavailableReason
            case CapabilityGuard.DEGRADED: return root.degradedReason
            case CapabilityGuard.LOADING: return "Cargando"
            default: return "Disponible"
        }
    }

    Keys.onEscapePressed: {
        if (root.state !== CapabilityGuard.AVAILABLE) {
            root.state = CapabilityGuard.AVAILABLE
        }
    }

    Loader {
        anchors.fill: parent
        sourceComponent: {
            switch (root.state) {
                case CapabilityGuard.LOADING:
                    return root.loadingContent
                case CapabilityGuard.UNAVAILABLE:
                    return root.unavailableContent
                case CapabilityGuard.DEGRADED:
                    return root.degradedContent
                default:
                    return root.availableContent
            }
        }
        onLoaded: item.objectName = root.objectName + "/active"
    }

    Item {
        id: fallback
        anchors.fill: parent
        visible: children.length > 0 && root.state === CapabilityGuard.AVAILABLE && root.availableContent === null
    }
}
