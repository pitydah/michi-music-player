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

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.OverBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HomeHero {
            }

            StatusBadge {
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
                visible: root.homeState !== HomePage.READY || !root.hb
            }

            ContinueCard {
                id: continueCard
                width: parent.width
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
            }

            Row {
                id: statusGrid
                width: parent.width
                spacing: MichiTheme.spacing.lg
                activeFocusOnTab: true
                KeyNavigation.tab: actionRow
                KeyNavigation.backtab: continueCard

                LibraryStatusCard {
                    id: libraryCard
                    width: parent.width * 0.48
                    albums: root.hb ? root.hb.libraryAlbums : 0
                    artists: root.hb ? root.hb.libraryArtists : 0
                    tracks: root.hb ? root.hb.libraryTracks : 0
                    hasData: root.hb ? root.hb.libraryAlbums > 0 || root.hb.libraryTracks > 0 : false
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
                    width: parent.width * 0.48
                    microServerState: root.cb ? root.cb.microServerState : "not_configured"
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
                    width: parent.width * 0.48
                    implicitHeight: 80
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
                    width: parent.width * 0.48
                    implicitHeight: 80
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
                        objectName: "homeResumeButton"
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
                width: parent.width
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
                text: root.statusMessage
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.statusMessage !== ""
            }
        }
    }

    Loader {
        active: root.homeState === HomePage.LOADING
        anchors.centerIn: parent
        sourceComponent: Column {
            spacing: MichiTheme.spacing.sm
            Repeater {
                model: 3
                MichiSkeleton { width: 320; height: 80 }
            }
        }
    }

    EmptyState {
        anchors.centerIn: parent
        visible: root.homeState === HomePage.EMPTY
        title: "Tu biblioteca está vacía"
        subtitle: "Añade una carpeta de música o conecta Michi Micro Server para comenzar."
        iconText: "♪"
        showAction: true
        actionText: "Añadir música"
        onActionClicked: {
            if (typeof navigationBridge !== "undefined")
                navigationBridge.navigate("library.sources")
        }
    }

    EmptyState {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 60
        visible: root.homeState === HomePage.EMPTY
        title: ""
        subtitle: "También puedes explorar la radio o conectar servidores Subsonic."
        iconText: ""
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
