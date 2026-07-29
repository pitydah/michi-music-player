import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    id: root
    objectName: "homeAudioHubPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Home Audio")

    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property bool loading: false
    property string pageError: ""
    readonly property bool hasComponents: root.bridge
                                          && (root.bridge.homeAssistantAvailable
                                              || root.bridge.snapcastAvailable
                                              || root.bridge.zonesSupported)
    readonly property int pageState: root.loading ? AsyncStateView.LOADING
                                                  : root.pageError !== "" ? AsyncStateView.ERROR
                                                                          : !root.bridge ? AsyncStateView.ERROR
                                                                                         : !root.hasComponents ? AsyncStateView.EMPTY
                                                                                                               : AsyncStateView.READY

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        root.refreshHub()
    }

    function refreshHub() {
        root.pageError = ""
        if (!root.bridge || typeof root.bridge.refresh !== "function") {
            root.loading = false
            root.pageError = qsTr("El servicio Home Audio no está disponible.")
            return
        }
        root.loading = true
        var result = root.bridge.refresh()
        if (result && result.pending)
            return
        root.loading = false
        if (result && result.ok === false)
            root.pageError = result.error || qsTr("No se pudo actualizar Home Audio.")
    }

    Connections {
        target: root.bridge
        function onOperationFinished(result) {
            if (!root.loading)
                return
            root.loading = false
            if (!result || result.ok === false)
                root.pageError = result && result.error
                                 ? result.error
                                 : qsTr("No se pudo actualizar Home Audio.")
        }
    }

    AsyncStateView {
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.LOADING
               ? qsTr("Actualizando Home Audio")
               : root.pageState === AsyncStateView.EMPTY
                 ? qsTr("Home Audio no está configurado")
                 : qsTr("No se pudo cargar Home Audio")
        message: root.pageState === AsyncStateView.LOADING
                 ? qsTr("Consultando servicios y dispositivos disponibles.")
                 : root.pageState === AsyncStateView.EMPTY
                   ? qsTr("Configura Home Assistant o conecta un receptor compatible para comenzar.")
                   : qsTr("Comprueba el servicio Home Audio e inténtalo de nuevo.")
        details: root.pageError
        retryAvailable: root.pageState === AsyncStateView.ERROR && root.bridge !== null
        primaryActionText: root.pageState === AsyncStateView.EMPTY ? qsTr("Actualizar") : ""
        onRetryRequested: root.refreshHub()
        onPrimaryActionRequested: root.refreshHub()

        readyContent: Flickable {
            id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width
                height: 140
                radius: MichiTheme.radius.lg
                showGlow: true

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: qsTr("Home Audio")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: qsTr("Audio multiroom, distribucion y planificacion de cadenas.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                text: qsTr("Componentes")
                width: parent.width
            }

            Grid {
                width: parent.width
                columns: responsive.columnCount
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                    height: 100
                    title: qsTr("Michi Music Stream")
                    subtitle: qsTr("Transmision de audio en tiempo real entre dispositivos.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.stream")
                    }
                }

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                    height: 100
                    title: qsTr("Habitaciones y zonas")
                    subtitle: qsTr("Gestion de zonas multiroom y agrupacion de dispositivos.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.rooms")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Parcial")
                        kind: "warning"
                    }
                }

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                    height: 100
                    title: qsTr("Distribucion de audio")
                    subtitle: qsTr("Fuentes, servidores, receptores y rutas activas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.distribution")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Parcial")
                        kind: "warning"
                    }
                }

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                    height: 100
                    title: qsTr("Planificador de cadenas")
                    subtitle: qsTr("Diseno y configuracion de cadenas de audio fisicas.")
                    variant: "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: clicked()
                    Keys.onSpacePressed: clicked()
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.chain_planner")
                    }

                    StatusBadge {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: MichiTheme.spacing.sm
                        text: qsTr("Planificado")
                        kind: "info"
                    }
                }
            }
        }
        }
    }
}
