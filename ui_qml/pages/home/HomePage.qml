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
    property var nb: typeof navigationBridge !== "undefined" ? navigationBridge : null

    enum State { LOADING, READY, EMPTY, ERROR }

    property int homeState: HomePage.LOADING
    property string statusMessage: ""

    function goToLibrary() { if (root.nb) root.nb.navigate("library") }
    function goToPlayback() { if (root.nb) root.nb.navigate("playback") }
    function goToRoute(r) { if (root.nb) root.nb.navigate(r) }
    function formatDuration(s) { if (!s) return ""; var m = Math.floor(s / 60); var sec = Math.floor(s % 60); return m + ":" + (sec < 10 ? "0" : "") + sec }

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
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HomeHero {}

            StatusBadge {
                text: root.homeState === HomePage.LOADING ? "Cargando..." : root.homeState === HomePage.ERROR ? "Error" : !root.hb ? "Servicio no disponible" : ""
                kind: root.homeState === HomePage.ERROR || !root.hb ? "error" : root.homeState === HomePage.LOADING ? "info" : "success"
                visible: root.homeState !== HomePage.READY || !root.hb
            }

            // Continuar escuchando
            ContinueCard {
                width: parent.width
                trackTitle: root.hb ? root.hb.currentTrackTitle : "—"
                trackArtist: root.hb ? root.hb.currentArtist : "—"
                hasPlayback: root.hb ? root.hb.hasPlayback : false
                visible: root.hb ? root.hb.hasPlayback : false
                activeFocusOnTab: true
                onActivate: root.goToPlayback()
            }

            // Biblioteca
            LibraryStatusCard {
                id: libraryCard
                width: parent.width
                albums: root.hb ? root.hb.libraryAlbums : 0
                artists: root.hb ? root.hb.libraryArtists : 0
                tracks: root.hb ? root.hb.libraryTracks : 0
                hasData: root.hb ? root.hb.libraryAlbums > 0 || root.hb.libraryTracks > 0 : false
                onOpenLibrary: root.goToLibrary()
            }

            // Álbumes recientes / Favoritos / Mixes
            Row {
                width: parent.width
                spacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.width * 0.48
                    implicitHeight: 100
                    activeFocusOnTab: true
                    Keys.onReturnPressed: root.goToRoute("library.recent")
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xs
                        Text { text: "Recién añadido"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Explora los últimos álbumes incorporados a tu biblioteca"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: parent.width; wrapMode: Text.WordWrap }
                        MichiButton { text: "Ver"; variant: "ghost"; onClicked: root.goToRoute("library.recent") }
                    }
                }

                GlassCard {
                    width: parent.width * 0.48
                    implicitHeight: 100
                    activeFocusOnTab: true
                    Keys.onReturnPressed: root.goToRoute("library.favorites")
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xs
                        Text { text: "Favoritos"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Tus canciones marcadas como favoritas"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: parent.width; wrapMode: Text.WordWrap }
                        MichiButton { text: "Ver"; variant: "ghost"; onClicked: root.goToRoute("library.favorites") }
                    }
                }
            }

            // Descubrir
            Row {
                width: parent.width
                spacing: MichiTheme.spacing.md

                GlassCard {
                    width: parent.width * 0.48
                    implicitHeight: 100
                    activeFocusOnTab: true
                    Keys.onReturnPressed: root.goToRoute("library.unplayed")
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xs
                        Text { text: "Sin reproducir"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Descubre música que aún no has escuchado"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: parent.width; wrapMode: Text.WordWrap }
                        MichiButton { text: "Explorar"; variant: "ghost"; onClicked: root.goToRoute("library.unplayed") }
                    }
                }

                GlassCard {
                    width: parent.width * 0.48
                    implicitHeight: 100
                    activeFocusOnTab: true
                    Keys.onReturnPressed: root.goToRoute("mix")
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xs
                        Text { text: "Mixes"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Listas inteligentes generadas para ti"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: parent.width; wrapMode: Text.WordWrap }
                        MichiButton { text: "Ver mixes"; variant: "ghost"; onClicked: root.goToRoute("mix") }
                    }
                }
            }

            // Ecosistema (compacto)
            EcosystemCard {
                width: parent.width
                microServerState: root.hb ? root.hb.ecosystemState || "not_configured" : "not_configured"
                onOpenConnections: root.goToRoute("connections")
                onOpenHomeAudio: root.goToRoute("home_audio")
            }

            // Michi AI (compacto)
            AssistantCard {
                width: parent.width
                onOpenAssistant: root.goToRoute("assistant")
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
                Skeleton { width: 320; height: 80 }
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
        onActionClicked: root.goToRoute("library.sources")
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
