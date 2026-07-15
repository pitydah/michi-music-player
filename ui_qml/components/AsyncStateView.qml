import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    id: root

    enum State {
        INITIALIZING,
        LOADING,
        READY,
        EMPTY,
        ERROR,
        UNAVAILABLE,
        DEGRADED
    }

    property int state: AsyncStateView.INITIALIZING
    property string objectName: "asyncStateView"

    property Component loadingContent: null
    property Component emptyContent: null
    property Component errorContent: null
    property Component unavailableContent: null
    property Component degradedContent: null
    property Component readyContent: null

    default property alias content: ready.content

    Accessible.role: Accessible.Panel
    Accessible.name: {
        switch (root.state) {
            case AsyncStateView.LOADING: return "Cargando"
            case AsyncStateView.EMPTY: return "Sin contenido"
            case AsyncStateView.ERROR: return "Error"
            case AsyncStateView.UNAVAILABLE: return "No disponible"
            case AsyncStateView.DEGRADED: return "Degradado"
            default: return "Contenido"
        }
    }

    Loader {
        id: activeLoader
        anchors.fill: parent
        sourceComponent: {
            switch (root.state) {
                case AsyncStateView.LOADING: return root.loadingContent
                case AsyncStateView.EMPTY: return root.emptyContent
                case AsyncStateView.ERROR: return root.errorContent
                case AsyncStateView.UNAVAILABLE: return root.unavailableContent
                case AsyncStateView.DEGRADED: return root.degradedContent
                case AsyncStateView.READY: return readyContent
                default: return null
            }
        }
        onLoaded: item.objectName = root.objectName + "/active"
    }

    Item {
        id: ready
        anchors.fill: parent
        visible: root.state === AsyncStateView.READY
    }
}
