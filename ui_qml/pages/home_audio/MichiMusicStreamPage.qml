import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"
import "../../components/foundations"

Item {
    objectName: "michiMusicStreamPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi Music Stream")

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property int pageState: stateLoading

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3
    readonly property int stateUnavailable: 4

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    readonly property string _statusText: {
        if (!root.ha) return ""
        var s = root.ha.streamState
        if (s === "playing") return qsTr("Transmitiendo audio a receptores")
        if (s === "paused") return qsTr("Transmisión en pausa")
        return qsTr("Sistema de transmisión de audio a equipos en la red local")
    }

    readonly property string _badgeText: {
        if (!root.ha) return qsTr("No disponible")
        var s = root.ha.streamState
        if (s === "playing") return qsTr("Transmitiendo")
        if (s === "paused") return qsTr("Pausado")
        return qsTr("Inactivo")
    }

    readonly property string _badgeKind: {
        if (!root.ha) return "disconnected"
        var s = root.ha.streamState
        if (s === "playing") return "success"
        if (s === "paused") return "warning"
        return "disconnected"
    }

    function routeEnter(route, params) {
        if (!root.ha) {
            root.pageState = stateUnavailable
            return
        }
        root.pageState = stateLoading
        if (typeof root.ha.refresh === "function")
            root.ha.refresh()
        var s = root.ha.streamState || "inactive"
        if (s === "error") root.pageState = stateError
        else if (s === "inactive") root.pageState = stateEmpty
        else root.pageState = stateReady
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: qsTr("Cargando Michi Music Stream") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState {
            message: qsTr("Error en la transmisión: ") + (root.ha ? root.ha.lastError : "")
            onRetryRequested: root.routeEnter("home_audio.stream", {})
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateUnavailable
        sourceComponent: UnavailableState {
            title: qsTr("Michi Music Stream no disponible")
            message: qsTr("Home Audio no está configurado. Configúralo desde Conexiones.")
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState {
            title: qsTr("Sin transmisión activa")
            subtitle: qsTr("Configura servidores Snapcast y receptores para comenzar a transmitir.")
            actionText: qsTr("Configurar distribución")
            onActionClicked: {
                if (typeof navigationBridge !== "undefined" && navigationBridge)
                    navigationBridge.navigate("home_audio.distribution")
            }
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        contentHeight: contentColumn.height + MichiTheme.spacing.xl
        clip: true
        visible: root.pageState === root.stateReady
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            // Stream status card
            GlassMaterial {
                width: parent.width
                height: responsive.compact ? 160 : 120
                variant: "base"
                radius: MichiTheme.radius.md

                GridLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    columns: responsive.compact ? 1 : 2
                    columnSpacing: MichiTheme.spacing.lg
                    rowSpacing: MichiTheme.spacing.sm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: MichiTheme.spacing.xs

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("Michi Music Stream")
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            Layout.fillWidth: true
                            text: root._statusText
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap
                        }
                    }

                    StatusBadge {
                        Layout.alignment: responsive.compact ? Qt.AlignLeft : Qt.AlignVCenter
                        text: root._badgeText
                        kind: root._badgeKind
                    }
                }
            }

            // Components grid
            Text {
                text: qsTr("Componentes del sistema")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Grid {
                width: parent.width
                columns: responsive.columnCount
                columnSpacing: MichiTheme.spacing.md
                rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: [
                        { title: qsTr("Receptores"), desc: qsTr("Dispositivos de audio en red"), icon: "devices" },
                        { title: qsTr("Salas y zonas"), desc: qsTr("Agrupación de receptores"), icon: "rooms" },
                        { title: qsTr("Transmisión local"), desc: qsTr("Streaming sin servidor externo"), icon: "home_audio" },
                        { title: qsTr("Multiroom"), desc: qsTr("Audio sincronizado en todas las salas"), icon: "streaming" },
                        { title: qsTr("Latencia"), desc: qsTr("Medición de delay en la red"), icon: "eq" },
                        { title: qsTr("Protocolo Michi"), desc: qsTr("Capa de transporte del ecosistema"), icon: "sync" }
                    ]

                    GlassCard {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        height: 96
                        title: modelData.title
                        subtitle: modelData.desc
                        variant: "base"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.md

                            MichiIcon {
                                iconKey: modelData.icon
                                size: 28
                                color: MichiTheme.colors.accentPrimary
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: modelData.title
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightMedium
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.desc
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            // Quick actions
            Text {
                text: qsTr("Acciones rápidas")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            RowLayout {
                width: parent.width
                spacing: MichiTheme.spacing.md

                MichiButton {
                    text: qsTr("Configurar distribución")
                    variant: "primary"
                    Layout.fillWidth: true
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.distribution")
                    }
                }

                MichiButton {
                    text: qsTr("Diagnóstico")
                    variant: "ghost"
                    Layout.fillWidth: true
                    onClicked: {
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.navigate("home_audio.rooms")
                    }
                }
            }
        }
    }

    Connections {
        target: root.ha
        function onStateChanged() {
            if (!root.ha) return
            var s = root.ha.streamState
            if (s === "error") root.pageState = stateError
            else if (s === "inactive") root.pageState = stateEmpty
            else root.pageState = stateReady
        }
    }
}
