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
    property string pendingRoute: ""
    property string previousRoute: ""
    property bool transitionRunning: false
    readonly property Loader _displayLoader: transitionRunning ? _incomingLoader : _activeLoader
    readonly property string loadedObjectName: _displayLoader && _displayLoader.item ? _displayLoader.item.objectName : ""
    property bool loading: false
    property string _prevRoute: ""
    property var _prevParams: ({})
    property int _loadGeneration: 0
    property Loader _activeLoader: loaderA
    property Loader _incomingLoader: loaderB

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
        pendingRoute = valid ? canonical : route
        lastError = ""
        lastRequestedSource = requestedSource
        loading = true
        _loadGeneration += 1
        var gen = _loadGeneration

        if (_activeLoader.item && typeof _activeLoader.item.routeLeave === "function") {
            _activeLoader.item.routeLeave(_prevRoute, _prevParams)
        }

        _incomingLoader.source = ""
        _incomingLoader.source = requestedSource
    }

    function getFallbackSource(route) {
        return "../pages/PlaceholderPage.qml"
    }

    function getRouteTitle(route) {
        return "Michi Music Player"
    }

    function callOnPage(methodName, firstArg, secondArg) {
        if (_activeLoader.item && typeof _activeLoader.item[methodName] === "function")
            _activeLoader.item[methodName](firstArg, secondArg)
    }

    function _swapLoaders() {
        var oldActive = _activeLoader
        _activeLoader = _incomingLoader
        _incomingLoader = oldActive
        _incomingLoader.opacity = 0
        _incomingLoader.visible = false
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteRefreshRequested(route) {
            root.callOnPage("routeRefresh", route, root.currentParams())
        }
        function onRouteParamsChanged() {
            if (_activeLoader.status === Loader.Ready)
                root.callOnPage("routeParamsChanged", root.currentRoute, root.currentParams())
        }
    }

    Item {
        objectName: "pageStackContainer"
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: MichiTheme.colors.bgApp
        }

        PageSurface {
            anchors.fill: parent
            anchors.leftMargin: root.width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.spacing.sm
            anchors.rightMargin: root.width < MichiTheme.breakpoints.compact ? 0 : MichiTheme.spacing.sm
            anchors.topMargin: MichiTheme.spacing.sm
            anchors.bottomMargin: MichiTheme.spacing.sm

            Loader {
                id: loaderA
                anchors.fill: parent
                asynchronous: true
                source: ""
                opacity: 1.0
                visible: true

                Behavior on opacity {
                    enabled: !MichiTheme.reducedMotion
                    NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
                }

                onStatusChanged: root._handleLoaderStatus(loaderA, status)
            }

            Loader {
                id: loaderB
                anchors.fill: parent
                asynchronous: true
                source: ""
                opacity: 0.0
                visible: false

                Behavior on opacity {
                    enabled: !MichiTheme.reducedMotion
                    NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
                }

                onStatusChanged: root._handleLoaderStatus(loaderB, status)
            }
        }
    }

    function _handleLoaderStatus(loader, status) {
        if (loader !== _incomingLoader)
            return
        if (status === Loader.Ready) {
            root.loading = false
            root.lastError = ""
            root.previousRoute = root.currentRoute
            root.currentRoute = root.pendingRoute
            root.lastLoadedRoute = root.currentRoute
            root.transitionRunning = true

            loader.opacity = 0
            loader.visible = true

            if (MichiTheme.reducedMotion) {
                loader.opacity = 1
                _activeLoader.opacity = 0
                _activeLoader.visible = false
                root._finalizeTransition()
            } else {
                loader.opacity = 1
                _activeLoader.opacity = 0
                transitionTimer.restart()
            }

            if (loader.item) {
                loader.item.forceActiveFocus()
                if (typeof loader.item.routeEnter === "function") {
                    loader.item.routeEnter(root.currentRoute, root.currentParams())
                }
            }
        } else if (status === Loader.Error) {
            root.loading = false
            root.lastError = qsTr("No se pudo cargar la ruta '%1' desde %2.")
                             .arg(root.pendingRoute).arg(root.lastRequestedSource)
            loader.source = ""
            loader.visible = false
            console.error("[PageStack] Route load error", root.pendingRoute, root.lastRequestedSource)
        } else if (status === Loader.Loading) {
            root.loading = true
        }
    }

    function _finalizeTransition() {
        if (_activeLoader !== _incomingLoader) {
            var oldLoader = _activeLoader
            _swapLoaders()
            oldLoader.source = ""
        }
        root.transitionRunning = false
    }

    Timer {
        id: transitionTimer
        interval: 180
        repeat: false
        onTriggered: root._finalizeTransition()
    }

    Timer {
        id: loadingIndicatorTimer
        interval: 120
        repeat: false
        onTriggered: {
            if (root.loading) loadingIndicator.visible = true
        }
    }

    onLoadingChanged: {
        if (loading) {
            loadingIndicatorTimer.restart()
        } else {
            loadingIndicatorTimer.stop()
            loadingIndicator.visible = false
        }
    }

    Rectangle {
        id: loadingIndicator
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        opacity: 0.6
        visible: false
        z: 50

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.md

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: loadingIndicator.visible
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: qsTr("Cargando…")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
            }
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: qsTr("Cargando contenido")
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

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: qsTr("Reintentar")
                    variant: "primary"
                    onClicked: {
                        root.lastError = ""
                        root.loadRoute(root.pendingRoute)
                    }
                }

                MichiButton {
                    text: qsTr("Ir a Inicio")
                    variant: "ghost"
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home")
                        root.lastError = ""
                    }
                }
            }
        }
    }
}
