import QtQuick
import "../theme"
import "states"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Async State View"
    objectName: "asyncStateView"
    focus: true
    id: root

    enum State {
        INITIALIZING = 0,
        LOADING,
        READY,
        EMPTY,
        ERROR,
        UNAVAILABLE,
        DEGRADED
    }

    property int state: AsyncStateView.INITIALIZING
    property string title: ""
    property string message: ""
    property string details: ""
    property string iconName: ""
    property string primaryActionText: ""
    property string secondaryActionText: ""
    property string errorCode: ""
    property string errorSource: ""
    property bool retryAvailable: true
    property bool reducedMotion: false

    property alias readyContent: readyHost.children
    property alias degradedOverlay: degradedHost.children

    signal primaryActionRequested()
    signal secondaryActionRequested()
    signal retryRequested()


return state === AsyncStateView.LOADING ? "Cargando" :
               state === AsyncStateView.ERROR ? "Error" + (title ? ": " + title : "") :
               state === AsyncStateView.EMPTY ? "Sin contenido" + (title ? ": " + title : "") :
               state === AsyncStateView.UNAVAILABLE ? "No disponible" :
               state === AsyncStateView.DEGRADED ? "Funcionamiento degradado" : ""
    }
    Accessible.description: message + (details ? ". " + details : "")

    Item {
        id: readyHost
        anchors.fill: parent
        visible: root.state === AsyncStateView.READY || root.state === AsyncStateView.DEGRADED
    }

    Item {
        id: stateLayer
        anchors.fill: parent
        visible: root.state !== AsyncStateView.READY

        Item {
            id: degradedHost
            anchors.fill: parent
            visible: root.state === AsyncStateView.DEGRADED
            z: 10
        }

        Loader {
            anchors.centerIn: parent
            width: Math.min(implicitWidth, parent.width * 0.85)
            active: root.state !== AsyncStateView.READY

            sourceComponent: {
                switch (root.state) {
                    case AsyncStateView.INITIALIZING:
                    case AsyncStateView.LOADING:
                        return loadingComp
                    case AsyncStateView.ERROR:
                        return errorComp
                    case AsyncStateView.EMPTY:
                        return emptyComp
                    case AsyncStateView.UNAVAILABLE:
                        return unavailableComp
                    default:
                        return null
                }
            }

            Component {
                id: loadingComp
                LoadingState {
                    title: root.title || "Cargando"
                    message: root.message || "Espera mientras se prepara el contenido."
                    reducedMotion: root.reducedMotion
                }
            }

            Component {
                id: errorComp
                ErrorState {
                    title: root.title
                    message: root.message || "No se pudo completar la operación."
                    details: root.details
                    errorCode: root.errorCode
                    errorSource: root.errorSource
                    showRetry: root.retryAvailable
                    reducedMotion: root.reducedMotion
                    onRetryRequested: root.retryRequested()
                    onPrimaryActionRequested: root.primaryActionRequested()
                    onSecondaryActionRequested: root.secondaryActionRequested()
                }
            }

            Component {
                id: emptyComp
                EmptyState {
                    title: root.title || "Sin contenido"
                    subtitle: root.message || "No hay elementos para mostrar."
                    iconText: root.iconName
                    showAction: root.primaryActionText !== ""
                    actionText: root.primaryActionText
                    onActionClicked: root.primaryActionRequested()
                }
            }

            Component {
                id: unavailableComp
                UnavailableState {
                    title: root.title
                    message: root.message || "Esta función no está disponible."
                    details: root.details
                }
            }
        }
    }
}
