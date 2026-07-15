import QtQuick
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import "../theme"
import "states"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
import QtQuick.Controls
import "../theme"
=======
import "../theme"
import "states"
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

Item {
    id: root

    enum State {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        INITIALIZING = 0,
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        INITIALIZING,
=======
        INITIALIZING = 0,
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        LOADING,
        READY,
        EMPTY,
        ERROR,
        UNAVAILABLE,
        DEGRADED
    }

    property int state: AsyncStateView.INITIALIZING
<<<<<<< Updated upstream
<<<<<<< Updated upstream
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
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property string objectName: "asyncStateView"
>>>>>>> Stashed changes

    property alias readyContent: readyHost.children
    property alias degradedOverlay: degradedHost.children

    signal primaryActionRequested()
    signal secondaryActionRequested()
    signal retryRequested()

    objectName: "AsyncStateView"

    Accessible.role: Accessible.Grouping
    Accessible.name: {
        if (state === AsyncStateView.LOADING) return "Cargando"
        if (state === AsyncStateView.ERROR) return "Error" + (title ? ": " + title : "")
        if (state === AsyncStateView.EMPTY) return "Sin contenido" + (title ? ": " + title : "")
        if (state === AsyncStateView.UNAVAILABLE) return "No disponible"
        if (state === AsyncStateView.DEGRADED) return "Funcionamiento degradado"
        return ""
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
<<<<<<< Updated upstream
=======
        visible: root.state === AsyncStateView.READY
=======
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

    objectName: "AsyncStateView"

    Accessible.role: Accessible.Grouping
    Accessible.name: {
        if (state === AsyncStateView.LOADING) return "Cargando"
        if (state === AsyncStateView.ERROR) return "Error" + (title ? ": " + title : "")
        if (state === AsyncStateView.EMPTY) return "Sin contenido" + (title ? ": " + title : "")
        if (state === AsyncStateView.UNAVAILABLE) return "No disponible"
        if (state === AsyncStateView.DEGRADED) return "Funcionamiento degradado"
        return ""
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
