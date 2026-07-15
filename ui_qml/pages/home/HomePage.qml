import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root

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

    Loader {
        id: stateLoader
        anchors.fill: parent
    }

    Component {
        id: loadingComp
        LoadingState {
            objectName: "home.loading"
            title: "Cargando centro Michi"
            message: "Obteniendo estado del ecosistema..."
        }
    }

    Component {
        id: emptyComp
        EmptyState {
            objectName: "home.empty"
            iconText: "♪"
            title: "Tu música te espera"
            subtitle: "Agrega carpetas con música para comenzar. Michi indexará tu biblioteca y mostrará tu resumen aquí."
            actionText: "Abrir biblioteca"
            showAction: true
            onActionClicked: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("library")
            }
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "home.error"
            title: "Inicio no disponible"
            message: root.hasBridge ? "Error al cargar el resumen del ecosistema." : "HomeBridge no está disponible."
            retryText: "Reconectar"
            onRetryRequested: {
                root.bridge = typeof homeBridge !== "undefined" ? homeBridge : null
                root.hasBridge = root.bridge !== null
                if (root.bridge) {
                    root.state = "READY"
                    root.bridge.refresh()
                }
            }
        }
    }

    Component {
        id: readyComp
        FocusScope {
            id: readyScope
            anchors.fill: parent
            activeFocusOnTab: true
            objectName: "home.focusScope"

            Keys.onEscapePressed: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home")
            }

            Flickable {
                id: flickable
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.xl
                contentHeight: column.height + MichiTheme.spacing.xxl
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                objectName: "home.flickableContent"

                Keys.onEscapePressed: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home")
                }

                Column {
                    id: column
                    width: parent.width
                    spacing: MichiTheme.spacing.lg

                    SectionHeader {
                        text: "Centro Michi"
                        Accessible.name: "Centro Michi"
                    }

                    JobStatusBanner {
                        id: jobBanner
                        width: parent.width
                        objectName: "home.jobBanner"
                        Accessible.name: "Trabajos activos"
                        KeyNavigation.tab: playbackCard
                    }

                    GlassMaterial {
                        id: playbackCard
                        width: parent.width
                        implicitHeight: 100
                        hovered: mousePlayback.containsMouse
                        interactive: true
                        radius: MichiTheme.radiusMd
                        objectName: "home.playbackCard"
                        Accessible.name: "Reproducción actual"

                        Keys.onReturnPressed: root.continuePlayback()
                        Keys.onSpacePressed: root.continuePlayback()

                        MouseArea {
                            id: mousePlayback
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.continuePlayback()
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.lg

                            Rectangle {
                                id: coverPlaceholder
                                width: 60; height: 60; radius: MichiTheme.radiusSm
                                color: MichiTheme.colors.accentSurface
                                border.color: MichiTheme.colors.borderCard
                                border.width: 1
                                visible: !root.bridge || !root.bridge.hasPlayback

                                Text {
                                    anchors.centerIn: parent
                                    text: "♪"
                                    color: MichiTheme.colors.accentBlue
                                    font.pixelSize: 24
                                    opacity: 0.50
                                }
                            }

                            Column {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    text: root.bridge && root.bridge.hasPlayback ? root.bridge.currentTrackTitle : "Sin reproducción activa"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.cardTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: root.bridge && root.bridge.hasPlayback ? root.bridge.currentArtist : "Reproduce tu música favorita"
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Row {
                                    spacing: MichiTheme.spacing.sm
                                    visible: root.bridge && root.bridge.hasPlayback

                                    StatusBadge {
                                        text: root.bridge && root.bridge.backend ? root.bridge.backend : ""
                                        kind: "info"
                                        visible: text !== ""
                                    }
                                }
                            }

                            Column {
                                Layout.alignment: Qt.AlignVCenter
                                spacing: MichiTheme.spacing.sm

                                MichiButton {
                                    text: root.bridge && root.bridge.hasPlayback ? "Continuar" : "Sin reproducción"
                                    variant: root.bridge && root.bridge.hasPlayback ? "accent" : "secondary"
                                    enabled: root.bridge && root.bridge.hasPlayback
                                    objectName: "home.continueButton"
                                    Accessible.name: "Continuar reproducción"
                                    KeyNavigation.tab: resumeBtn
                                    onClicked: root.continuePlayback()
                                }

                                MichiButton {
                                    id: resumeBtn
                                    text: "Reanudar cola"
                                    variant: "ghost"
                                    enabled: root.bridge && root.bridge.hasPlayback
                                    objectName: "home.resumeQueueButton"
                                    Accessible.name: "Reanudar cola de reproducción"
                                    KeyNavigation.tab: libraryStatusCard
                                    onClicked: root.resumeQueue()
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: MichiTheme.spacing.lg

                        GlassMaterial {
                            id: libraryStatusCard
                            width: parent.width * 0.48
                            implicitHeight: 180
                            hovered: mouseLib.containsMouse
                            interactive: true
                            radius: MichiTheme.radiusMd
                            objectName: "home.libraryStatusCard"
                            Accessible.name: "Estado de la biblioteca"

                            Keys.onReturnPressed: root.openSource()
                            Keys.onSpacePressed: root.openSource()

                            MouseArea {
                                id: mouseLib
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.openSource()
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.lg
                                spacing: MichiTheme.spacing.md

                                Text {
                                    text: "Biblioteca"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    Accessible.name: "Biblioteca"
                                }

                                Row {
                                    spacing: MichiTheme.spacing.xl
                                    Repeater {
                                        model: [
                                            { label: "Álbumes", value: root.bridge ? root.bridge.libraryAlbums : 0 },
                                            { label: "Artistas", value: root.bridge ? root.bridge.libraryArtists : 0 },
                                            { label: "Canciones", value: root.bridge ? root.bridge.libraryTracks : 0 }
                                        ]
                                        Column {
                                            spacing: MichiTheme.spacing.xs
                                            Text {
                                                text: modelData.value
                                                color: modelData.label === "Álbumes" ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                                                font.pixelSize: MichiTheme.typography.heroTitleSize
                                                font.weight: MichiTheme.typography.weightBold
                                            }
                                            Text {
                                                text: modelData.label
                                                color: MichiTheme.colors.textMuted
                                                font.pixelSize: MichiTheme.typography.metaSize
                                            }
                                        }
                                    }
                                }

                                Text {
                                    text: {
                                        if (!root.bridge) return "Bridge no disponible"
                                        var s = root.bridge.sourcesCount + " fuente" + (root.bridge.sourcesCount !== 1 ? "s" : "")
                                        if (root.bridge.lastScan) s += " · Último escaneo: " + root.bridge.lastScan
                                        return s
                                    }
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                MichiButton {
                                    text: "Explorar"
                                    variant: "secondary"
                                    objectName: "home.exploreLibraryButton"
                                    Accessible.name: "Explorar biblioteca"
                                    KeyNavigation.tab: serverStatusCard
                                    onClicked: root.openSource()
                                }
                            }
                        }

                        GlassMaterial {
                            id: serverStatusCard
                            width: parent.width * 0.48
                            implicitHeight: 180
                            hovered: mouseServer.containsMouse
                            interactive: true
                            radius: MichiTheme.radiusMd
                            objectName: "home.serverStatusCard"
                            Accessible.name: "Estado del servidor"

                            Keys.onReturnPressed: root.reconnectServer()
                            Keys.onSpacePressed: root.reconnectServer()

                            MouseArea {
                                id: mouseServer
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.reconnectServer()
                            }

                            Column {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.lg
                                spacing: MichiTheme.spacing.md

                                Text {
                                    text: "Micro Server"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    Accessible.name: "Micro Server"
                                }

                                Row {
                                    spacing: MichiTheme.spacing.sm
                                    StatusBadge { text: "No configurado"; kind: "disconnected" }
                                    StatusBadge { text: "Experimental"; kind: "experimental" }
                                }

                                Text {
                                    text: "Servidor musical doméstico del ecosistema Michi. Comparte tu biblioteca en la red local."
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                }

                                Row {
                                    spacing: MichiTheme.spacing.sm
                                    MichiButton {
                                        text: "Conectar"
                                        variant: "primary"
                                        objectName: "home.connectServerButton"
                                        Accessible.name: "Conectar al servidor"
                                        KeyNavigation.tab: assistantCard
                                        onClicked: root.reconnectServer()
                                    }
                                    MichiButton {
                                        text: "Jobs"
                                        variant: "ghost"
                                        visible: root.bridge && root.bridge.activeJobs > 0
                                        objectName: "home.openJobsButton"
                                        Accessible.name: "Abrir trabajos activos"
                                        onClicked: root.openJobs()
                                    }
                                }
                            }
                        }
                    }

                    GlassMaterial {
                        id: assistantCard
                        width: parent.width
                        implicitHeight: 80
                        hovered: mouseAssistant.containsMouse
                        interactive: true
                        radius: MichiTheme.radiusMd
                        objectName: "home.assistantCard"
                        Accessible.name: "Asistente Michi AI"

                        Keys.onReturnPressed: root.openAssistant()
                        Keys.onSpacePressed: root.openAssistant()

                        MouseArea {
                            id: mouseAssistant
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.openAssistant()
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.lg

                            Column {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    text: "Asistente Michi"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.cardTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }

                                Text {
                                    text: "Pregunta sobre tu música, recibe sugerencias y controla tu biblioteca con IA."
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    lineHeight: 1.4
                                }
                            }

                            MichiButton {
                                text: "Abrir"
                                variant: "ghost"
                                objectName: "home.openAssistantButton"
                                Accessible.name: "Abrir asistente"
                                KeyNavigation.tab: jobBanner
                                onClicked: root.openAssistant()
                            }
                        }
                    }
                }
            }
        }
    }
}
