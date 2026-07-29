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
    property bool _distributionActive: false
    property int _activeRoomCount: 0
    property int _receiverCount: 0
    property string _currentTrack: ""
    property string _currentArtist: ""
    property string _streamState: ""

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
        root._updateDashboard()
    }

    function _updateDashboard() {
        if (!root.bridge) return
        root._streamState = root.bridge.streamState || ""
        root._distributionActive = root.bridge.localPlaybackRouteable || false
        var zones = root.bridge.zones || []
        var receivers = root.bridge.receiverList || []
        root._activeRoomCount = zones.length
        root._receiverCount = receivers.length
    }

    Connections {
        target: root.bridge
        function onStateChanged() {
            root._updateDashboard()
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
                   ? qsTr("Configura dispositivos o conecta un receptor para comenzar.")
                   : qsTr("Comprueba el servicio e inténtalo de nuevo.")
        details: root.pageError
        retryAvailable: root.pageState === AsyncStateView.ERROR && root.bridge !== null
        primaryActionText: root.pageState === AsyncStateView.EMPTY ? qsTr("Actualizar") : ""
        onRetryRequested: root.refreshHub()
        onPrimaryActionRequested: root.refreshHub()

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            contentHeight: column.height + MichiTheme.spacing.xl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                // Hero — Distribution status
                HeroMaterial {
                    width: parent.width
                    height: responsive.compact ? 200 : 160
                    radius: MichiTheme.radius.lg
                    showGlow: root._distributionActive

                    GridLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xl
                        columns: responsive.compact ? 1 : 2
                        columnSpacing: MichiTheme.spacing.lg

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: qsTr("Home Audio")
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.heroTitleSize
                                font.weight: MichiTheme.typography.weightBold
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root._distributionActive
                                    ? qsTr("Distribuyendo audio a ") + root._activeRoomCount + qsTr(" habitaciones")
                                    : qsTr("Audio multiroom para tu hogar")
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root._currentTrack
                                    ? root._currentTrack + " — " + root._currentArtist
                                    : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                visible: root._currentTrack !== ""
                                elide: Text.ElideRight
                            }
                        }

                        ColumnLayout {
                            Layout.alignment: Qt.AlignRight
                            spacing: MichiTheme.spacing.sm

                            StatusBadge {
                                text: root._distributionActive ? qsTr("Transmitiendo") : qsTr("Inactivo")
                                kind: root._distributionActive ? "success" : "disconnected"
                                Layout.alignment: Qt.AlignRight
                            }

                            Text {
                                text: root._receiverCount + qsTr(" receptores") + " · " + root._activeRoomCount + qsTr(" zonas")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                Layout.alignment: Qt.AlignRight
                            }
                        }
                    }
                }

                // Health row — system status
                Flow {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    StatusBadge {
                        text: root.bridge && root.bridge.snapcastAvailable
                            ? qsTr("Snapserver disponible")
                            : qsTr("Snapserver no disponible")
                        kind: root.bridge && root.bridge.snapcastAvailable ? "success" : "disconnected"
                    }

                    StatusBadge {
                        text: root.bridge && root.bridge.homeAssistantAvailable
                            ? qsTr("Home Assistant conectado")
                            : qsTr("Home Assistant no configurado")
                        kind: root.bridge && root.bridge.homeAssistantAvailable ? "success" : "info"
                    }

                    StatusBadge {
                        text: root._distributionActive ? qsTr("Distribución activa") : qsTr("Distribución inactiva")
                        kind: root._distributionActive ? "success" : "disconnected"
                    }
                }

                // Active rooms — direct control cards
                SectionHeader {
                    text: qsTr("Zonas activas")
                    width: parent.width
                }

                Loader {
                    width: parent.width
                    active: root._activeRoomCount > 0
                    sourceComponent: roomGrid
                }

                Loader {
                    width: parent.width
                    active: root._activeRoomCount === 0
                    sourceComponent: Component {
                        GlassCard {
                            width: parent.width
                            height: 80
                            title: qsTr("Sin zonas activas")
                            subtitle: qsTr("Configura habitaciones desde la sección de distribución.")
                            variant: "base"
                        }
                    }
                }

                // Quick navigation
                SectionHeader {
                    text: qsTr("Secciones")
                    width: parent.width
                }

                Grid {
                    width: parent.width
                    columns: responsive.columnCount
                    columnSpacing: MichiTheme.spacing.md
                    rowSpacing: MichiTheme.spacing.md

                    GlassCard {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        height: 80
                        title: qsTr("Michi Music Stream")
                        subtitle: qsTr("Transmisión y distribución de audio.")
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
                        height: 80
                        title: qsTr("Zonas y dispositivos")
                        subtitle: qsTr("Agrupación y control de receptores.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("home_audio.rooms")
                        }
                    }

                    GlassCard {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        height: 80
                        title: qsTr("Distribución avanzada")
                        subtitle: qsTr("Fuentes, rutas y servidores.")
                        variant: "base"
                        activeFocusOnTab: true
                        Keys.onReturnPressed: clicked()
                        Keys.onSpacePressed: clicked()
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("home_audio.distribution")
                        }
                    }
                }
            }
        }
    }

    Component {
        id: roomGrid

        Grid {
            width: parent.width
            columns: responsive.columnCount
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.md

            Repeater {
                model: root.bridge ? (root.bridge.zones || []) : []

                GlassCard {
                    width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                    height: 120
                    variant: "base"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: modelData.name || qsTr("Zona sin nombre")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium
                            elide: Text.ElideRight
                        }

                        Text {
                            text: {
                                var devs = modelData.receivers || modelData.members || []
                                return devs.length + qsTr(" dispositivos")
                            }
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.xs

                            MichiButton {
                                text: qsTr("Volumen")
                                variant: "ghost"
                                Layout.fillWidth: true
                                implicitHeight: 28
                                onClicked: {
                                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                                        navigationBridge.navigate("zone_detail", { zoneId: modelData.id })
                                }
                            }

                            MichiButton {
                                text: qsTr("Abrir")
                                variant: "primary"
                                Layout.fillWidth: true
                                implicitHeight: 28
                                onClicked: {
                                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                                        navigationBridge.navigate("zone_detail", { zoneId: modelData.id })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
