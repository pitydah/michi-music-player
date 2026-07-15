import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Inicio"

    property var hb: typeof homeBridge !== "undefined" ? homeBridge : null
    property var cb: typeof connectionsBridge !== "undefined" ? connectionsBridge : null
    property var jb: typeof jobBridge !== "undefined" ? jobBridge : null

    enum State {
        LOADING,
        READY,
        EMPTY,
        ERROR
    }

    property int homeState: HomePage.LOADING
    property string statusMessage: ""

    function refresh() {
        if (root.hb && typeof root.hb.refresh !== "undefined") {
            root.hb.refresh()
            root.homeState = HomePage.READY
            root.statusMessage = ""
        } else {
            root.homeState = HomePage.ERROR
            root.statusMessage = "Servicio de inicio no disponible"
        }
    }

    Component.onCompleted: root.refresh()

    property var bridge: typeof homeBridge !== "undefined" ? homeBridge : null
    property string state: "LOADING"
    property string appState: "ready"
    property bool hasBridge: root.bridge !== null

    objectName: "home.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Inicio"
    Accessible.description: "Panel principal con resumen del estado del ecosistema musical"

    signal continuePlayback()
    signal resumeQueue()
    signal reconnectServer()
    signal openJobs()
    signal openSource()
    signal openProblem(string problemId)
    signal openAssistant()

    states: [
        State { name: "LOADING"; PropertyChanges { target: stateLoader; sourceComponent: loadingComp } },
        State { name: "READY"; PropertyChanges { target: stateLoader; sourceComponent: readyComp } },
        State { name: "EMPTY"; PropertyChanges { target: stateLoader; sourceComponent: emptyComp } },
        State { name: "ERROR"; PropertyChanges { target: stateLoader; sourceComponent: errorComp } }
    ]

    Component.onCompleted: {
        if (root.bridge) {
            root.state = "READY"
            root.bridge.refresh()
        } else {
            root.state = "ERROR"
        }
    }

    Keys.onEscapePressed: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("home")
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Tab) {
            if (stateLoader.item && stateLoader.item.hasOwnProperty("forceActiveFocus")) {
                stateLoader.item.forceActiveFocus()
            }
        }
    }

    Loader {
        id: stateLoader
        anchors.fill: parent
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    }
=======
>>>>>>> Stashed changes
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    Component {
        id: loadingComp
        LoadingState {
            objectName: "home.loading"
            title: "Cargando centro Michi"
            message: "Obteniendo estado del ecosistema..."
            Accessible.name: "Cargando centro Michi"
        }
    }

<<<<<<< Updated upstream
            HomeHero {
                objectName: "homeHero"
                Accessible.name: "Hero de inicio"
=======
<<<<<<< HEAD
    Component {
        id: emptyComp
        EmptyState {
            objectName: "home.empty"
            iconText: "♪"
            title: "Tu música te espera"
            subtitle: "Agrega carpetas con música para comenzar. Michi indexará tu biblioteca y mostrará tu resumen aquí."
            actionText: "Abrir biblioteca"
            showAction: true
            Accessible.name: "Inicio vacío"
            onActionClicked: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("library")
=======
            HomeHero {
                objectName: "homeHero"
                Accessible.name: "Hero de inicio"
            }

            StatusBadge {
                objectName: "homeStatusBadge"
                text: {
                    if (root.homeState === HomePage.LOADING) return "Cargando..."
                    if (root.homeState === HomePage.ERROR) return "Error"
                    if (!root.hb) return "Servicio no disponible"
                    return "Ready"
                }
                kind: {
                    if (root.homeState === HomePage.ERROR || !root.hb) return "error"
                    if (root.homeState === HomePage.LOADING) return "info"
                    return "success"
                }
                Accessible.name: "Estado: " + text
                visible: root.homeState !== HomePage.READY || !root.hb
            }

            ContinueCard {
                id: continueCard
                width: parent.width
                objectName: "continueCard"
                Accessible.name: "Continuar reproducción"
                trackTitle: root.hb ? root.hb.currentTrackTitle : "—"
                trackArtist: root.hb ? root.hb.currentArtist : "—"
                hasPlayback: root.hb ? root.hb.hasPlayback : false
                activeFocusOnTab: true
                KeyNavigation.tab: statusGrid
                KeyNavigation.backtab: column
                Keys.onReturnPressed: activate()
                Keys.onSpacePressed: activate()
                onActivate: {
                    if (root.hb && root.hb.hasPlayback && typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("playback")
                }
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }

<<<<<<< Updated upstream
            StatusBadge {
                objectName: "homeStatusBadge"
                text: {
                    if (root.homeState === HomePage.LOADING) return "Cargando..."
                    if (root.homeState === HomePage.ERROR) return "Error"
                    if (!root.hb) return "Servicio no disponible"
                    return "Ready"
                }
                kind: {
                    if (root.homeState === HomePage.ERROR || !root.hb) return "error"
                    if (root.homeState === HomePage.LOADING) return "info"
                    return "success"
                }
                Accessible.name: "Estado: " + text
                visible: root.homeState !== HomePage.READY || !root.hb
            }

            ContinueCard {
                id: continueCard
                width: parent.width
                objectName: "continueCard"
                Accessible.name: "Continuar reproducción"
                trackTitle: root.hb ? root.hb.currentTrackTitle : "—"
                trackArtist: root.hb ? root.hb.currentArtist : "—"
                hasPlayback: root.hb ? root.hb.hasPlayback : false
                activeFocusOnTab: true
                KeyNavigation.tab: statusGrid
                KeyNavigation.backtab: column
                Keys.onReturnPressed: activate()
                Keys.onSpacePressed: activate()
                onActivate: {
                    if (root.hb && root.hb.hasPlayback && typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("playback")
=======
<<<<<<< HEAD
    Component {
        id: errorComp
        ErrorState {
            objectName: "home.error"
            title: "Inicio no disponible"
            message: root.hasBridge ? "Error al cargar el resumen del ecosistema." : "HomeBridge no está disponible."
            retryText: "Reconectar"
            Accessible.name: "Error en inicio"
            onRetryRequested: {
                root.bridge = typeof homeBridge !== "undefined" ? homeBridge : null
                root.hasBridge = root.bridge !== null
                if (root.bridge) {
                    root.state = "READY"
                    root.bridge.refresh()
=======
            Row {
                id: statusGrid
                width: parent.width
                spacing: MichiTheme.spacing.lg
                activeFocusOnTab: true
                KeyNavigation.tab: actionRow
                KeyNavigation.backtab: continueCard

                LibraryStatusCard {
                    id: libraryCard
                    objectName: "libraryCard"
                    width: parent.width * 0.48
                    albums: root.hb ? root.hb.libraryAlbums : 0
                    artists: root.hb ? root.hb.libraryArtists : 0
                    tracks: root.hb ? root.hb.libraryTracks : 0
                    hasData: root.hb ? root.hb.libraryAlbums > 0 || root.hb.libraryTracks > 0 : false
                    Accessible.name: "Estado de la biblioteca"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onOpenLibrary()
                    Keys.onSpacePressed: onOpenLibrary()
                    onOpenLibrary: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("library")
                    }
>>>>>>> Stashed changes
                }

                EcosystemCard {
                    id: ecosystemCard
                    objectName: "ecosystemCard"
                    width: parent.width * 0.48
                    microServerState: root.cb ? root.cb.microServerState : "not_configured"
                    Accessible.name: "Ecosistema"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onOpenConnections()
                    Keys.onSpacePressed: onOpenConnections()
                    onOpenConnections: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("connections")
                    }
                    onOpenHomeAudio: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }
            }

            Row {
                id: actionRow
                width: parent.width
                spacing: MichiTheme.spacing.lg
                KeyNavigation.tab: microCard
                KeyNavigation.backtab: statusGrid

                GlassCard {
                    id: microCard
                    objectName: "microServerCard"
                    width: parent.width * 0.48
                    implicitHeight: 80
                    Accessible.name: "Servidor Micro"
                    activeFocusOnTab: true

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Micro Server"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        StatusBadge {
                            text: root.cb && root.cb.microServerState === "connected" ? "Activo" : "Detenido"
                            kind: root.cb && root.cb.microServerState === "connected" ? "success" : "disconnected"
                        }
                    }
                }

                GlassCard {
                    id: jobsCard
                    objectName: "jobsCard"
                    width: parent.width * 0.48
                    implicitHeight: 80
                    Accessible.name: "Trabajos activos"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("jobs")
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Trabajos activos"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: root.jb ? String(root.jb.activeCount) : "0"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            text: "Ver trabajos"
                            variant: "ghost"
                            onClicked: {
                                if (typeof navigationBridge !== "undefined")
                                    navigationBridge.navigate("jobs")
                            }
                        }
                    }
                }
            }

            GlassCard {
                id: playbackCard
                objectName: "playbackInfoCard"
                width: parent.width
                implicitHeight: 60
                visible: root.hb && root.hb.hasPlayback
                Accessible.name: "Información de reproducción"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    CoverImage {
                        width: 40
                        height: 40
                        coverRadius: MichiTheme.radiusSm
                        coverKey: root.hb && root.hb.hasPlayback ? "NOWPLAYING" : ""
                        visible: root.hb && root.hb.hasPlayback
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: root.hb ? root.hb.currentTrackTitle : ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: root.hb ? root.hb.currentArtist : ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }

                    StatusBadge {
                        text: {
                            var src = root.hb ? root.hb.backend : ""
                            if (src === "gstreamer") return "Local"
                            if (src === "mpd") return "MPD"
                            if (src && src.indexOf("radio") >= 0) return "Radio"
                            if (src && src.indexOf("subsonic") >= 0) return "Subsonic"
                            return src || "—"
                        }
                        kind: root.hb && root.hb.hasPlayback ? "active" : "disconnected"
                    }

                    MichiButton {
                        text: "Reanudar"
                        variant: "accent"
                        enabled: root.hb && root.hb.hasPlayback
                        onClicked: {
                            if (root.hb && root.hb.hasPlayback && typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("playback")
                        }
                    }
                }
            }

            AssistantCard {
                id: assistantCard
                objectName: "assistantCard"
                width: parent.width
                Accessible.name: "Asistente Michi"
                activeFocusOnTab: true
                KeyNavigation.backtab: playbackCard
                Keys.onReturnPressed: onOpenAssistant()
                Keys.onSpacePressed: onOpenAssistant()
                onOpenAssistant: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("assistant")
>>>>>>> origin/michi-qml-functional-wave
                }
            }

            Text {
                objectName: "homeErrorMessage"
                text: root.statusMessage
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.statusMessage !== ""
                Accessible.name: "Error: " + root.statusMessage
            }
        }
    }

<<<<<<< Updated upstream
            Row {
                id: statusGrid
                width: parent.width
                spacing: MichiTheme.spacing.lg
                activeFocusOnTab: true
                KeyNavigation.tab: actionRow
                KeyNavigation.backtab: continueCard
=======
<<<<<<< HEAD
    Component {
        id: readyComp
        FocusScope {
            id: readyScope
            anchors.fill: parent
            activeFocusOnTab: true
            objectName: "home.focusScope"
>>>>>>> Stashed changes

                LibraryStatusCard {
                    id: libraryCard
                    objectName: "libraryCard"
                    width: parent.width * 0.48
                    albums: root.hb ? root.hb.libraryAlbums : 0
                    artists: root.hb ? root.hb.libraryArtists : 0
                    tracks: root.hb ? root.hb.libraryTracks : 0
                    hasData: root.hb ? root.hb.libraryAlbums > 0 || root.hb.libraryTracks > 0 : false
                    Accessible.name: "Estado de la biblioteca"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onOpenLibrary()
                    Keys.onSpacePressed: onOpenLibrary()
                    onOpenLibrary: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("library")
                    }
                }

                EcosystemCard {
                    id: ecosystemCard
                    objectName: "ecosystemCard"
                    width: parent.width * 0.48
                    microServerState: root.cb ? root.cb.microServerState : "not_configured"
                    Accessible.name: "Ecosistema"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onOpenConnections()
                    Keys.onSpacePressed: onOpenConnections()
                    onOpenConnections: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("connections")
                    }
                    onOpenHomeAudio: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio")
                    }
                }
            }

            Row {
                id: actionRow
                width: parent.width
                spacing: MichiTheme.spacing.lg
                KeyNavigation.tab: microCard
                KeyNavigation.backtab: statusGrid

                GlassCard {
                    id: microCard
                    objectName: "microServerCard"
                    width: parent.width * 0.48
                    implicitHeight: 80
                    Accessible.name: "Servidor Micro"
                    activeFocusOnTab: true

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Micro Server"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        StatusBadge {
                            text: root.cb && root.cb.microServerState === "connected" ? "Activo" : "Detenido"
                            kind: root.cb && root.cb.microServerState === "connected" ? "success" : "disconnected"
                        }
                    }
                }

                GlassCard {
                    id: jobsCard
                    objectName: "jobsCard"
                    width: parent.width * 0.48
                    implicitHeight: 80
                    Accessible.name: "Trabajos activos"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("jobs")
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Trabajos activos"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: root.jb ? String(root.jb.activeCount) : "0"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            text: "Ver trabajos"
                            variant: "ghost"
                            onClicked: {
                                if (typeof navigationBridge !== "undefined")
                                    navigationBridge.navigate("jobs")
                            }
                        }
                    }
                }
            }

            GlassCard {
                id: playbackCard
                objectName: "playbackInfoCard"
                width: parent.width
                implicitHeight: 60
                visible: root.hb && root.hb.hasPlayback
                Accessible.name: "Información de reproducción"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    CoverImage {
                        width: 40
                        height: 40
                        coverRadius: MichiTheme.radiusSm
                        coverKey: root.hb && root.hb.hasPlayback ? "NOWPLAYING" : ""
                        visible: root.hb && root.hb.hasPlayback
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: root.hb ? root.hb.currentTrackTitle : ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: root.hb ? root.hb.currentArtist : ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }

                    StatusBadge {
                        text: {
                            var src = root.hb ? root.hb.backend : ""
                            if (src === "gstreamer") return "Local"
                            if (src === "mpd") return "MPD"
                            if (src && src.indexOf("radio") >= 0) return "Radio"
                            if (src && src.indexOf("subsonic") >= 0) return "Subsonic"
                            return src || "—"
                        }
                        kind: root.hb && root.hb.hasPlayback ? "active" : "disconnected"
                    }

                    MichiButton {
                        text: "Reanudar"
                        variant: "accent"
                        enabled: root.hb && root.hb.hasPlayback
                        onClicked: {
                            if (root.hb && root.hb.hasPlayback && typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("playback")
                        }
                    }
                }
            }

            AssistantCard {
                id: assistantCard
                objectName: "assistantCard"
                width: parent.width
                Accessible.name: "Asistente Michi"
                activeFocusOnTab: true
                KeyNavigation.backtab: playbackCard
                Keys.onReturnPressed: onOpenAssistant()
                Keys.onSpacePressed: onOpenAssistant()
                onOpenAssistant: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("assistant")
                }
            }

            Text {
                objectName: "homeErrorMessage"
                text: root.statusMessage
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.statusMessage !== ""
                Accessible.name: "Error: " + root.statusMessage
            }
        }
    }

    LoadingState {
        objectName: "homeLoadingState"
        anchors.centerIn: parent
        visible: root.homeState === HomePage.LOADING
        title: "Cargando inicio"
        Accessible.name: "Cargando panel de inicio"
    }

<<<<<<< Updated upstream
=======
    function routeRefresh(route) {
        if (root.bridge) {
            root.bridge.refresh()
        }
=======
    LoadingState {
        objectName: "homeLoadingState"
        anchors.centerIn: parent
        visible: root.homeState === HomePage.LOADING
        title: "Cargando inicio"
        Accessible.name: "Cargando panel de inicio"
    }

>>>>>>> Stashed changes
    EmptyState {
        objectName: "homeEmptyState"
        anchors.centerIn: parent
        visible: root.homeState === HomePage.EMPTY
        title: "No hay datos disponibles"
        subtitle: "Conecta una fuente de música o revisa la configuración."
        iconText: ""
        Accessible.name: "Panel de inicio vacío"
    }

    ErrorState {
        objectName: "homeErrorState"
        anchors.centerIn: parent
        visible: root.homeState === HomePage.ERROR
        title: "Error al cargar inicio"
        message: root.statusMessage
        Accessible.name: "Error en panel de inicio"
        showRetry: true
        onRetryRequested: root.refresh()
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
}
