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
    readonly property var currentPage: _displayLoader && _displayLoader.item
                                       ? _displayLoader.item
                                       : null
    property bool loading: false
    property string _prevRoute: ""
    property var _prevParams: ({})
    property int _loadGeneration: 0
    property Loader _activeLoader: loaderA
    property Loader _incomingLoader: loaderB
    // Track whether the pending route renders a degraded/placeholder page so
    // the load outcome can be surfaced as routeUnavailableRendered.
    property bool _pendingDegraded: false
    property string _pendingDegradedReason: ""

    // Every navigation request ends in exactly one of these outcomes.
    signal routeLoaded(string route)
    signal routeUnavailableRendered(string route, string reason)
    signal routeErrorRendered(string route, string reason)

    function currentParams() {
        return typeof navigationBridge !== "undefined" && navigationBridge
               ? navigationBridge.currentParams : ({})
    }

    function loadRoute(route) {
        // If a cross-fade is mid-flight, finalize it first so the visible page
        // is promoted to active and the freed loader becomes the new incoming.
        // Without this, reusing _incomingLoader would destroy the page the user
        // is currently looking at (transition race).
        if (root.transitionRunning) {
            transitionTimer.stop()
            root._finalizeTransition()
        }

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

        // A route is "degraded" when it is unknown (renders the generic
        // placeholder) or when its registry status is not "functional"
        // (renders a FeatureStatePage). Functional routes emit routeLoaded.
        var degradeReason = ""
        if (!valid) {
            degradeReason = qsTr("Route not found")
        } else if (registry && registry.getStatus(canonical) !== "functional") {
            degradeReason = registry.getStatus(canonical)
        }
        _pendingDegraded = degradeReason !== ""
        _pendingDegradedReason = degradeReason

        if (_activeLoader.item && typeof _activeLoader.item.routeLeave === "function") {
            _activeLoader.item.routeLeave(_prevRoute, _prevParams)
        }

        _incomingLoader.source = ""
        // Re-enable in case this loader was disabled by a prior finalize.
        _incomingLoader.enabled = true
        // Stamp the generation so stale loads can be discarded on completion.
        _incomingLoader.requestGeneration = _loadGeneration
        _incomingLoader.requestedRoute = pendingRoute
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
        clip: true

        Rectangle {
            anchors.fill: parent
            // Dark opaque backdrop so cross-fades never show through to the
            // surface below during the atomic page swap.
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
                property int requestGeneration: -1
                property string requestedRoute: ""
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
                property int requestGeneration: -1
                property string requestedRoute: ""
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
            // Disable and release the old page before the new one takes over
            // so there is no window where both pages are interactive.
            oldLoader.enabled = false
            oldLoader.visible = false
            oldLoader.opacity = 0
            oldLoader.source = ""
            _swapLoaders()
        }
        root.transitionRunning = false
    }

    Timer {
        id: transitionTimer
        interval: 180
        repeat: false
        onTriggered: root._finalizeTransition()
    }

}
