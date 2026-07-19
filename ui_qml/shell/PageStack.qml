import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"

Item {
    id: root
    objectName: "pageStack"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Contenido principal")

    property var registry: typeof routeRegistryBridge !== "undefined" ? routeRegistryBridge : null
    property string currentRoute: "home"
    property string lastError: ""
    property string lastLoadedRoute: ""
    property string lastRequestedSource: ""
    readonly property string loadedObjectName: pageLoader.item ? pageLoader.item.objectName : ""
    property bool loading: false
    property string _prevRoute: ""
    property var _prevParams: ({})

    function currentParams() {
        return typeof navigationBridge !== "undefined" && navigationBridge
               ? navigationBridge.currentParams : ({})
    }

    function loadRoute(route) {
        var canonical = registry ? registry.resolveRoute(route) : route
        var valid = registry ? registry.isValidRoute(route) : false
        var requestedSource = valid ? registry.getSource(canonical) : getFallbackSource(route)
        if (!requestedSource) requestedSource = getFallbackSource(route)
        _prevRoute = currentRoute
        _prevParams = root.currentParams()
        currentRoute = valid ? canonical : route
        lastError = ""
        lastRequestedSource = requestedSource
        loading = true
        callOnPage("routeLeave", _prevRoute, _prevParams)
        pageLoader.source = ""
        pageLoader.source = requestedSource
    }

    function getFallbackSource(route) {
        return "../pages/PlaceholderPage.qml"
    }

    function getRouteTitle(route) {
        return "Michi Music Player"
    }

    function callOnPage(methodName, firstArg, secondArg) {
        if (pageLoader.item && typeof pageLoader.item[methodName] === "function")
            pageLoader.item[methodName](firstArg, secondArg)
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteRefreshRequested(route) {
            root.callOnPage("routeRefresh", route, root.currentParams())
        }
        function onRouteParamsChanged() {
            if (pageLoader.status === Loader.Ready)
                root.callOnPage("routeParamsChanged", root.currentRoute, root.currentParams())
        }
    }

    Loader {
        id: pageLoader
        anchors.fill: parent
        asynchronous: true
        source: ""

        opacity: status === Loader.Ready ? 1.0 : 0.0
        Behavior on opacity {
            NumberAnimation { duration: MichiTheme.motion.fast; easing.type: Easing.OutCubic }
        }

        onStatusChanged: {
            if (status === Loader.Ready) {
                root.loading = false
                root.lastError = ""
                root.lastLoadedRoute = root.currentRoute
                root.callOnPage("routeEnter", root.currentRoute, root.currentParams())
            } else if (status === Loader.Error) {
                root.loading = false
                root.lastError = qsTr("No se pudo cargar la ruta '%1' desde %2. Consulta los diagnósticos QML anteriores para conocer el error de componente.")
                                 .arg(root.currentRoute).arg(root.lastRequestedSource)
                console.error("[PageStack] Route load error", root.currentRoute, root.lastRequestedSource,
                              "Loader status:", status)
            } else if (status === Loader.Loading) {
                root.loading = true
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: pageLoader.status === Loader.Null && root.currentRoute !== "" && !root.loading
        z: -1
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: root.lastError !== ""
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
