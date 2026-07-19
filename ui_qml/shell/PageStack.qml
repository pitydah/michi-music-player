import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Stack"
    objectName: "pageStack"
    focus: true
    id: root

    property var registry: typeof routeRegistryBridge !== "undefined" ? routeRegistryBridge : null
    property string currentRoute: "home"
    property string lastError: ""
    property string lastLoadedRoute: ""
    property string lastRequestedSource: ""
    readonly property string loadedObjectName: pageLoader.item ? pageLoader.item.objectName : ""
    property bool loading: false
    property string _prevRoute: ""

    function loadRoute(route) {
        var canonical = registry ? registry.resolveRoute(route) : route
        var valid = registry ? registry.isValidRoute(route) : false
        var requestedSource = valid ? registry.getSource(canonical) : getFallbackSource(route)
        if (!requestedSource) requestedSource = getFallbackSource(route)
        _prevRoute = currentRoute
        currentRoute = valid ? canonical : route
        lastError = ""
        lastRequestedSource = requestedSource
        loading = true
        callOnPage("routeLeave", _prevRoute)
        pageLoader.source = ""
        pageLoader.source = requestedSource
    }

    function getFallbackSource(route) {
        return "../pages/PlaceholderPage.qml"
    }

    function getRouteTitle(route) {
        return "Michi Music Player"
    }

    function callOnPage(methodName, arg) {
        if (pageLoader.item && typeof pageLoader.item[methodName] === "function") {
            pageLoader.item[methodName](arg)
        }
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteRefreshRequested(route) {
            callOnPage("routeRefresh", route)
        }
    }

    PageStackContainer {
        id: pageLoader
        anchors.fill: parent
        asynchronous: true
        source: ""

        onStatusChanged: {
            if (status === Loader.Ready) {
                loading = false
                lastError = ""
                lastLoadedRoute = currentRoute
                callOnPage("routeEnter", currentRoute)
            } else if (status === Loader.Error) {
                loading = false
                lastError = qsTr("No se pudo cargar la ruta '%1' desde %2. Consulta los diagnósticos QML anteriores para conocer el error de componente.").arg(currentRoute).arg(lastRequestedSource)
                console.error("[PageStack] Route load error", currentRoute, lastRequestedSource,
                              "Loader status:", status)
            } else if (status === Loader.Loading) {
                loading = true
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgContent
        visible: root.loading
        z: 90

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md
            BusyIndicator { anchors.horizontalCenter: parent.horizontalCenter; running: root.loading }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Cargando contenido")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgContent
        visible: lastError !== ""
        z: 100

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md
            width: Math.min(400, parent.width * 0.8)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Error de ruta")
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightBold
            }

            Text {
                width: parent.width
                text: root.lastError
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            MichiButton {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Ir a Inicio")
                variant: "primary"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                    root.lastError = ""
                }
            }
        }
    }
}
