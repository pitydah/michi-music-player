import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/layout"
import "../../materials"
import "."

MichiPage {
    id: root
    objectName: "homePage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Inicio"

    property var hb: typeof homeBridge !== "undefined" ? homeBridge : null
    property var nb: typeof navigationBridge !== "undefined" ? navigationBridge : null

    enum State { LOADING, READY, EMPTY, ERROR }

    property int homeState: HomePage.LOADING
    property string statusMessage: ""
    readonly property int libraryTracks: root.hb ? Number(root.hb.libraryTracks || 0) : 0
    readonly property int sourcesCount: root.hb ? Number(root.hb.sourcesCount || 0) : 0
    readonly property int activeJobs: root.hb ? Number(root.hb.activeJobs || 0) : 0
    readonly property int quickColumns: width >= 1500 ? 4 : width >= 900 ? 2 : 1
    readonly property bool hasLibrary: libraryTracks > 0
    visualState: homeState === HomePage.ERROR ? "error" : "content"
    maximumContentWidth: 1360

    function setHomeState(value, message) {
        root.homeState = value
        root.state = value === HomePage.LOADING ? "LOADING"
                   : value === HomePage.READY ? "READY"
                   : value === HomePage.EMPTY ? "EMPTY" : "ERROR"
        root.statusMessage = message || ""
    }

    function updateState() {
        if (!root.hb) {
            root.setHomeState(HomePage.ERROR, qsTr("Servicio de inicio no disponible"))
        } else if (root.libraryTracks > 0) {
            root.setHomeState(HomePage.READY, "")
        } else if (root.sourcesCount === 0) {
            root.setHomeState(HomePage.EMPTY, "")
        } else if (root.activeJobs > 0) {
            root.setHomeState(HomePage.LOADING, qsTr("Escaneando tu biblioteca"))
        } else {
            root.setHomeState(HomePage.READY, qsTr("Fuente configurada. Inicia un escaneo para añadir música."))
        }
    }

    function refresh() {
        if (!root.hb || typeof root.hb.refresh === "undefined") {
            root.setHomeState(HomePage.ERROR, qsTr("Servicio de inicio no disponible"))
            return
        }
        root.setHomeState(HomePage.LOADING, qsTr("Actualizando Inicio"))
        try {
            var ok = root.hb.refresh()
            if (ok === false)
                root.setHomeState(HomePage.ERROR, qsTr("No se pudo actualizar Inicio"))
            else
                root.updateState()
        } catch (error) {
            root.setHomeState(HomePage.ERROR, qsTr("No se pudo actualizar Inicio"))
        }
    }

    function goToRoute(route) {
        if (root.nb) root.nb.navigate(route)
    }

    Component.onCompleted: root.refresh()

    Connections {
        target: root.hb
        function onSnapshotChanged() { root.updateState() }
    }

    Column {
        id: contentColumn
        objectName: "homeContent"
        width: parent.width
        spacing: MichiTheme.spacing.lg

            HomeHero {
                id: hero
                width: parent.width
                message: root.homeState === HomePage.EMPTY
                         ? qsTr("Prepara tu biblioteca local o conecta tu servidor Michi.")
                         : root.homeState === HomePage.LOADING
                           ? qsTr("Estamos actualizando el estado de tu música.")
                           : qsTr("Tu biblioteca y el ecosistema Michi, listos en un solo lugar.")
                primaryText: root.homeState === HomePage.EMPTY ? qsTr("Añadir carpeta") : qsTr("Explorar biblioteca")
                secondaryText: qsTr("Conectar servidor")
                onPrimaryAction: root.goToRoute(root.homeState === HomePage.EMPTY ? "library.sources" : "library")
                onSecondaryAction: root.goToRoute("connections")
            }

            GlassMaterial {
                objectName: "homeLoadingCard"
                width: parent.width
                height: 88
                visible: root.homeState === HomePage.LOADING
                variant: "status"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    BusyIndicator {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        running: parent.parent.visible
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text {
                            text: root.statusMessage || qsTr("Cargando biblioteca")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                        Text {
                            text: qsTr("El contenido aparecerá en cuanto termine la actualización.")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }
                }
            }

            GlassMaterial {
                objectName: "homeEmptyWelcome"
                width: parent.width
                height: 180
                visible: root.homeState === HomePage.EMPTY
                variant: "elevated"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xl

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.sm

                        Text {
                            objectName: "homeEmptyTitle"
                            Layout.fillWidth: true
                            text: qsTr("Tu música comienza aquí")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }
                        Text {
                            objectName: "homeEmptyDescription"
                            Layout.fillWidth: true
                            text: qsTr("Añade una carpeta local o conecta Michi Micro Server para construir tu biblioteca.")
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
                    }

                    ColumnLayout {
                        Layout.preferredWidth: 190
                        Layout.alignment: Qt.AlignVCenter
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            Layout.fillWidth: true
                            text: qsTr("Añadir carpeta")
                            variant: "primary"
                            onClicked: root.goToRoute("library.sources")
                        }
                        MichiButton {
                            Layout.fillWidth: true
                            text: qsTr("Conectar servidor")
                            variant: "secondary"
                            onClicked: root.goToRoute("connections")
                        }
                    }
                }
            }

            ContinueCard {
                width: parent.width
                trackTitle: root.hb ? root.hb.currentTrackTitle : "—"
                trackArtist: root.hb ? root.hb.currentArtist : "—"
                hasPlayback: root.hb ? root.hb.hasPlayback : false
                visible: root.homeState === HomePage.READY && hasPlayback
                activeFocusOnTab: visible
                onActivate: root.goToRoute("playback")
            }

            LibraryStatusCard {
                id: libraryCard
                width: parent.width
                visible: root.homeState === HomePage.READY
                albums: root.hb ? root.hb.libraryAlbums : 0
                artists: root.hb ? root.hb.libraryArtists : 0
                tracks: root.libraryTracks
                hasData: root.hasLibrary
                onOpenLibrary: root.goToRoute("library")
            }

            MichiResponsiveGrid {
                id: quickGrid
                objectName: "homeQuickGrid"
                width: parent.width
                visible: root.homeState === HomePage.READY && root.hasLibrary
                requestedColumns: root.quickColumns
                maximumColumns: 4
                minimumCellWidth: 260
                spacing: MichiTheme.spacing.md

                Repeater {
                    model: [
                        { title: qsTr("Recién añadido"), description: qsTr("Explora los últimos álbumes incorporados a tu biblioteca"), action: qsTr("Ver recientes"), route: "library.recent" },
                        { title: qsTr("Favoritos"), description: qsTr("Vuelve a las canciones que has marcado como favoritas"), action: qsTr("Ver favoritos"), route: "library.favorites" },
                        { title: qsTr("Sin reproducir"), description: qsTr("Descubre música de tu biblioteca que aún no has escuchado"), action: qsTr("Explorar"), route: "library.unplayed" },
                        { title: qsTr("Mixes"), description: qsTr("Escucha selecciones inteligentes construidas para ti"), action: qsTr("Ver mixes"), route: "mix" }
                    ]

                    MichiFeatureCard {
                        required property var modelData
                        height: 144
                        title: modelData.title
                        description: modelData.description
                        primaryActionText: modelData.action
                        route: modelData.route
                        iconKey: modelData.route === "mix" ? "mix"
                                 : modelData.route === "library.recent" ? "history"
                                 : "library"
                        featureAccessibleName: modelData.title
                        onClicked: root.goToRoute(modelData.route)
                    }
                }
            }

            EcosystemCard {
                width: parent.width
                visible: root.homeState === HomePage.READY
                microServerState: root.hb && root.hb.ecosystemState ? root.hb.ecosystemState : "not_configured"
                onOpenConnections: root.goToRoute("connections")
                onOpenHomeAudio: root.goToRoute("home_audio")
            }

            AssistantCard {
                width: parent.width
                visible: root.homeState === HomePage.READY
                onOpenAssistant: root.goToRoute("assistant")
            }

            Text {
                width: parent.width
                text: root.statusMessage
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root.homeState === HomePage.READY && root.statusMessage !== ""
                wrapMode: Text.WordWrap
            }
    }

    stateContent: Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: root.homeState === HomePage.ERROR

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(420, parent.width - MichiTheme.spacing.xxl)
            spacing: MichiTheme.spacing.md

            Text {
                Layout.fillWidth: true
                text: qsTr("No pudimos cargar Inicio")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                Layout.fillWidth: true
                text: root.statusMessage
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
            MichiButton {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("Reintentar")
                variant: "primary"
                onClicked: root.refresh()
            }
        }
    }
}
