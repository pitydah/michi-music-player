import QtQuick
import QtQuick.Controls
import "../theme"

Item {
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

    Accessible.role: Accessible.Panel
    Accessible.name: root.capabilityName !== "" ? root.capabilityName : "Capacidad"

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
    }

    Item {
        id: fallback
        anchors.fill: parent
        visible: children.length > 0 && root.state === CapabilityGuard.AVAILABLE && root.availableContent === null
    }
}
