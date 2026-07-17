import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/states"
import "."

Item {
    objectName: "homePage"
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

    function updateStateFromBridge() {
        if (!root.hb) {
            root.homeState = HomePage.ERROR
            root.statusMessage = "Servicio de inicio no disponible"
            return
        }
        root.statusMessage = root.hb.errorMessage || ""
        if (root.hb.loading) {
            root.homeState = HomePage.LOADING
        } else if (!root.hb.ready && root.statusMessage !== "") {
            root.homeState = HomePage.ERROR
        } else if (!root.hb.hasLibrary && root.hb.sourcesCount === 0) {
            root.homeState = HomePage.EMPTY
        } else {
            root.homeState = HomePage.READY
        }
    }

    function refresh() {
        if (!root.hb || typeof root.hb.refresh === "undefined") {
            root.homeState = HomePage.ERROR
            root.statusMessage = "Servicio de inicio no disponible"
            return
        }
        root.homeState = HomePage.LOADING
        root.statusMessage = ""
        var result = root.hb.refresh()
        root.updateStateFromBridge()
        if (result && result.ok === false && !root.hb.ready) {
            root.homeState = HomePage.ERROR
            root.statusMessage = result.errors ? result.errors.join("; ") : "No se pudo cargar el inicio"
        }
    }

    Component.onCompleted: root.refresh()

    Connections {
        target: root.hb
        function onSnapshotChanged() {
            root.updateStateFromBridge()
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true
        visible: root.homeState === HomePage.READY

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HomeHero {
                width: parent.width
            }

            StatusBadge {
                text: root.statusMessage !== "" ? "Información parcial" : "Listo"
                kind: root.statusMessage !== "" ? "warning" : "success"
                visible: root.statusMessage !== ""
            }

            ContinueCard {
                id: continueCard
                width: parent.width
                trackTitle: root.hb ? root.hb.currentTrackTitle : "—"
                trackArtist: root.hb ? root.hb.currentArtist : "—"
                hasPlayback: root.hb ? root.hb.hasPlayback : false
                activeFocusOnTab: true
                KeyNavigation.tab: libraryCard
                Keys.onReturnPressed: continueCard.activate()
                Keys.onSpacePressed: continueCard.activate()
                onActivate: {
                    if (root.hb && root.hb.hasPlayback && typeof navigationBridge !== "undefined")
                        navigationBridge.navigate("playback")
                }
            }

            Row {
                id: statusGrid
                width: parent.width
                spacing: MichiTheme.spacing.lg

                LibraryStatusCard {
                    id: libraryCard
                    width: parent.width * 0.48
                    albums: root.hb ? root.hb.libraryAlbums : 0
                    artists: root.hb ? root.hb.libraryArtists : 0
                    tracks: root.hb ? root.hb.libraryTracks : 0
                    hasData: root.hb ? root.hb.hasLibrary : false
                    activeFocusOnTab: true
                    KeyNavigation.tab: ecosystemCard
                    KeyNavigation.backtab: continueCard
                    Keys.onReturnPressed: libraryCard.openLibrary()
                    Keys.onSpacePressed: libraryCard.openLibrary()
                    onOpenLibrary: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("library")
                    }
                }

                EcosystemCard {
                    id: ecosystemCard
                    width: parent.width * 0.48
                    microServerState: root.cb ? root.cb.microServerState : "not_configured"
                    activeFocusOnTab: true
                    KeyNavigation.tab: microCard
                    KeyNavigation.backtab: libraryCard
                    Keys.onReturnPressed: ecosystemCard.openConnections()
                    Keys.onSpacePressed: ecosystemCard.openConnections()
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

                GlassCard {
                    id: microCard
                    width: parent.width * 0.48
                    implicitHeight: 80
                    activeFocusOnTab: true
                    KeyNavigation.tab: jobsCard
                    KeyNavigation.backtab: ecosystemCard
                    Keys.onReturnPressed: {
                        if (typeof navigationBridge !== "undefined")
                            navigationBridge.navigate("connections")
                    }

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

                        Item { Layout.fillWidth: true }

                        StatusBadge {
                            text: root.cb && root.cb.microServerState === "connected" ? "Activo" : "Detenido"
                            kind: root.cb && root.cb.microServerState === "connected" ? "success" : "disconnected"
                        }
                    }
                }

                GlassCard {
                    id: jobsCard
                    width: parent.width * 0.48
                    implicitHeight: 80
                    activeFocusOnTab: true
                    KeyNavigation.backtab: microCard
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
                            text: root.hb ? String(root.hb.activeJobs) : "0"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            objectName: "homeViewJobsButton"
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
                width: parent.width
                implicitHeight: 60
                visible: root.hb && root.hb.hasPlayback

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    CoverImage {
                        width: 40
                        height: 40
                        coverRadius: MichiTheme.radiusSm
                        coverKey: root.hb && root.hb.hasPlayback ? "NOWPLAYING" : ""
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.xs

                        Text {
                            width: parent.width
                            text: root.hb ? root.hb.currentTrackTitle : ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                        }

                        Text {
                            width: parent.width
                            text: root.hb ? root.hb.currentArtist : ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
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
                        kind: "active"
                    }

                    MichiButton {
                        objectName: "homeResumeButton"
                        text: "Reanudar"
                        variant: "accent"
                        enabled: root.hb && root.hb.hasPlayback
                        onClicked: {
                            if (typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("playback")
                        }
                    }
                }
            }

            AssistantCard {
                id: assistantCard
                width: parent.width
                activeFocusOnTab: true
                Keys.onReturnPressed: assistantCard.openAssistant()
                Keys.onSpacePressed: assistantCard.openAssistant()
                onOpenAssistant: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("assistant")
                }
            }

            MichiBanner {
                width: parent.width
                visible: root.statusMessage !== ""
                kind: "warning"
                message: root.statusMessage
            }
        }
    }

    LoadingState {
        anchors.centerIn: parent
        visible: root.homeState === HomePage.LOADING
        title: "Cargando inicio"
        subtitle: "Actualizando biblioteca, reproducción y ecosistema."
    }

    EmptyState {
        anchors.centerIn: parent
        visible: root.homeState === HomePage.EMPTY
        title: "Tu biblioteca está vacía"
        subtitle: "Añade una carpeta de música o conecta Michi Micro Server para comenzar."
        iconText: "library"
        showAction: true
        actionText: "Añadir música"
        onActionClicked: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("library.sources")
        }
    }

    ErrorState {
        anchors.centerIn: parent
        visible: root.homeState === HomePage.ERROR
        title: "Error al cargar inicio"
        message: root.statusMessage
        showRetry: true
        onRetryRequested: root.refresh()
    }
}
