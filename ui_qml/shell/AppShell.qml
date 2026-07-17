import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"
import "."

Item {
    id: root
    objectName: "appShell"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Aplicación Michi"

    property alias currentRoute: sidebar.currentRoute
    property alias pageTitle: header.pageTitle
    property var cmdPalette: commandPalette
    property bool fatalError: false
    property string fatalMessage: ""

    MichiResponsive { id: responsive; availableWidth: root.width }

    function updateHeaderTitle(route) {
        if (typeof routeRegistryBridge !== "undefined" && routeRegistryBridge) {
            header.pageTitle = routeRegistryBridge.getTitle(route)
        } else {
            header.pageTitle = pageStack.getRouteTitle(route)
        }
    }

    function showFatal(message) {
        root.fatalError = true
        root.fatalMessage = message
    }

    function dismissFatal() {
        root.fatalError = false
        root.fatalMessage = ""
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 0

            Sidebar {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: sidebar.implicitWidth
                Layout.minimumWidth: sidebar.implicitWidth
                Layout.maximumWidth: sidebar.implicitWidth
                autoCollapsed: responsive.sidebarAutoCollapse
                currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"

                onRouteRequested: function(route) {
                    if (typeof navigationBridge !== "undefined" && navigationBridge) {
                        navigationBridge.navigate(route)
                    } else {
                        pageStack.loadRoute(route)
                        sidebar.currentRoute = route
                        root.updateHeaderTitle(route)
                    }
                }
            }

            Rectangle {
                id: sidebarResizeHandle
                Layout.fillHeight: true
                Layout.preferredWidth: visible ? 4 : 0
                Layout.minimumWidth: Layout.preferredWidth
                Layout.maximumWidth: Layout.preferredWidth
                visible: !sidebar.collapsed && !sidebar.autoCollapsed
                color: resizeMouse.containsMouse ? MichiTheme.colors.borderHover : "transparent"

                Behavior on color {
                    ColorAnimation { duration: MichiTheme.motion.durationFast }
                }

                MouseArea {
                    id: resizeMouse
                    anchors.fill: parent
                    anchors.leftMargin: -4
                    anchors.rightMargin: -4
                    hoverEnabled: true
                    cursorShape: Qt.SizeHorCursor
                    property real pressX: 0
                    property real startWidth: sidebar.expandedWidth

                    onPressed: function(mouse) {
                        pressX = mouse.x
                        startWidth = sidebar.expandedWidth
                    }

                    onPositionChanged: function(mouse) {
                        if (!(mouse.buttons & Qt.LeftButton))
                            return
                        var requested = startWidth + mouse.x - pressX
                        sidebar.expandedWidth = Math.max(180, Math.min(420, requested))
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                HeaderBar {
                    id: header
                    Layout.fillWidth: true
                    Layout.preferredHeight: MichiTheme.headerHeight
                    pageTitle: "Inicio"
                    canGoBack: navigationBridge ? navigationBridge.canGoBack : false
                    canGoForward: navigationBridge ? navigationBridge.canGoForward : false
                    routeHistory: navigationBridge ? navigationBridge.history : []

                    DragHandler {
                        target: null
                        acceptedButtons: Qt.LeftButton
                        onActiveChanged: {
                            if (active && root.Window.window)
                                root.Window.window.startSystemMove()
                        }
                    }

                    onBackClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }

                    onForwardClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.forward()
                    }

                    onBreadcrumbClicked: function(route) {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate(route)
                    }
                }

                PageStack {
                    id: pageStack
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentRoute: navigationBridge ? navigationBridge.currentRoute : "home"
                }
            }
        }

        NowPlayingBar {
            id: nowPlayingBar
            Layout.fillWidth: true
            Layout.preferredHeight: MichiTheme.nowPlayingHeight
            Layout.maximumHeight: MichiTheme.nowPlayingHeight
            Layout.minimumHeight: MichiTheme.nowPlayingHeight
            z: 10
        }
    }

    CommandPalette {
        id: commandPalette
        anchors.fill: parent
        cpb: typeof commandPaletteBridge !== "undefined" ? commandPaletteBridge : null
    }

    ShortcutLayer {
        anchors.fill: parent
        cmdPalette: commandPalette
    }

    NotificationCenter {
        id: notificationCenter
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: MichiTheme.headerHeight
        anchors.rightMargin: MichiTheme.spacing.md
        width: 360
        height: Math.min(400, parent.height * 0.5)
        z: 9997
        nb: typeof notificationBridge !== "undefined" ? notificationBridge : null
    }

    Rectangle {
        id: loadingOverlay
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9999
        visible: pageStack.loading
        objectName: "loadingOverlay"

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg
            width: Math.min(320, parent.width * 0.6)

            MichiProgressBar {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                indeterminate: true
                objectName: "loadingProgressBar"
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Cargando..."
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Cargando contenido"
    }

    Rectangle {
        id: errorOverlay
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        z: 9999
        visible: pageStack.lastError !== "" && !root.fatalError

        ErrorState {
            anchors.centerIn: parent
            width: Math.min(440, parent.width * 0.8)
            title: "No se pudo abrir la página"
            message: pageStack.lastError
            errorSource: pageStack.currentRoute
            showRetry: true
            onRetryRequested: pageStack.loadRoute(pageStack.currentRoute)
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Error de carga de página"
    }

    Rectangle {
        id: fatalOverlay
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        z: 10000
        visible: root.fatalError
        objectName: "fatalOverlay"

        ErrorState {
            anchors.centerIn: parent
            width: Math.min(440, parent.width * 0.8)
            title: "Error fatal"
            message: root.fatalMessage
            showRetry: false
            primaryActionText: "Cerrar aviso"
            onPrimaryActionRequested: root.dismissFatal()
        }

        Accessible.role: Accessible.AlertMessage
        Accessible.name: "Error fatal de la aplicación"
    }

    Connections {
        target: typeof navigationBridge !== "undefined" ? navigationBridge : null
        function onRouteChanged(route) {
            pageStack.loadRoute(route)
            sidebar.currentRoute = route
            root.updateHeaderTitle(route)
        }
    }

    Component.onCompleted: {
        if (typeof navigationBridge !== "undefined" && navigationBridge) {
            var initial = navigationBridge.currentRoute
            pageStack.loadRoute(initial)
            sidebar.currentRoute = initial
            root.updateHeaderTitle(initial)
        } else {
            pageStack.loadRoute("home")
        }
    }

    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]

        Rectangle {
            anchors.fill: parent
            color: MichiTheme.colors.accentSurface
            border.width: 2
            border.color: MichiTheme.colors.accentBlue
            radius: MichiTheme.radius.lg
            visible: parent.containsDrag
            z: 10000

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.md

                MichiIcon {
                    anchors.horizontalCenter: parent.horizontalCenter
                    iconName: "library"
                    iconSize: 32
                    accessibleName: "Añadir música"
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Suelta los archivos para añadirlos a la biblioteca"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                }
            }
        }

        onDropped: function(drop) {
            if (!drop.hasUrls)
                return

            var lib = typeof libraryBridge !== "undefined" ? libraryBridge : null
            var notif = typeof notificationBridge !== "undefined" ? notificationBridge : null
            var accepted = false

            for (var i = 0; i < drop.urls.length; i++) {
                var droppedPath = drop.urls[i].toLocalFile()
                if (!droppedPath)
                    continue
                if (!lib || typeof lib.addMedia === "undefined") {
                    if (notif)
                        notif.showMessage("La biblioteca no está disponible", "error")
                    break
                }

                var result = lib.addMedia(droppedPath)
                var ok = result && result.ok
                accepted = accepted || ok
                if (notif) {
                    var filename = droppedPath.split("/").pop()
                    var message = ok ? "Añadido: " + filename
                                     : "No se pudo añadir " + filename + ": "
                                       + (result && result.error ? result.error : "error desconocido")
                    notif.showMessage(message, ok ? "success" : "error")
                }
            }

            if (accepted)
                drop.accept()
        }

        Accessible.role: Accessible.Pane
        Accessible.name: "Área para añadir archivos"
    }
}
