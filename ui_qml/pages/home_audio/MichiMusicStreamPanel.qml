import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi Music Stream")
    objectName: "michiMusicStreamPanel"
    focus: true
    id: root

    property string streamState: "inactive"
    property bool loading: false
    property bool hasError: false
    property string lastError: ""
    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    implicitHeight: responsive.compact ? 720 : 420

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        if (!root.bridge) return
        root.loading = true
        var s = root.bridge.streamState
        if (s !== undefined) {
            root.streamState = s
            root.hasError = s === "error"
        }
        root.loading = false
    }

    readonly property string _statusText: {
        if (root.loading) return qsTr("Cargando estado del stream...")
        if (root.hasError) return qsTr("Error en la transmisión: ") + root.lastError
        if (root.streamState === "playing") return qsTr("Transmitiendo audio a receptores")
        if (root.streamState === "paused") return qsTr("Transmisión en pausa")
        if (root.streamState === "inactive") return qsTr("Sistema propio del ecosistema Michi para transmitir música a receptores y equipos de audio dentro de la red local.")
        return qsTr("Estado conceptual — configure servidores y receptores para activar")
    }

    readonly property string _badgeKind: {
        if (root.loading) return "info"
        if (root.hasError) return "error"
        if (root.streamState === "playing") return "success"
        if (root.streamState === "paused") return "warning"
        return "experimental"
    }

    readonly property string _badgeText: {
        if (root.loading) return qsTr("Cargando")
        if (root.hasError) return qsTr("Error")
        if (root.streamState === "playing") return qsTr("Transmitiendo")
        if (root.streamState === "paused") return qsTr("Pausado")
        if (root.streamState === "inactive") return qsTr("Inactivo")
        return qsTr("Concepto")
    }

    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg

        GlassMaterial {
            width: parent.width
            height: responsive.compact ? 144 : 104
            variant: "base"
            radius: MichiTheme.radius.md

            GridLayout {
                anchors.fill: parent
                anchors.margins: responsive.compact
                                 ? MichiTheme.spacing.md
                                 : MichiTheme.spacing.lg
                columns: responsive.compact ? 1 : 2
                columnSpacing: MichiTheme.spacing.lg
                rowSpacing: MichiTheme.spacing.sm

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
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
                        color: root.hasError ? MichiTheme.colors.error
                                             : MichiTheme.colors.textSecondary
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

        // Loading state
        Loader {
            active: root.loading
            sourceComponent: LoadingState { title: qsTr("Cargando estado del sistema") }
        }

        // Error state
        Loader {
            active: root.hasError && !root.loading
            sourceComponent: ErrorState { message: root.lastError || qsTr("Error desconocido en la transmisión") }
        }

        // Empty/inactive state
        Loader {
            active: root.streamState === "inactive" && !root.loading && !root.hasError
            sourceComponent: EmptyState {
                title: qsTr("Sin transmisión activa")
                actionText: qsTr("Configurar servidor Snapcast")
                onActionClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("home_audio.distribution")
                }
            }
        }

        // Ready state — show system components
        Loader {
            active: !root.loading && !root.hasError && root.streamState !== "inactive"
            sourceComponent: systemComponents
        }
    }

    Component {
        id: systemComponents

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.md

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
                        { title: qsTr("Receptores Michi"), desc: qsTr("Dispositivos de audio en red") },
                        { title: qsTr("Salas y zonas"), desc: qsTr("Agrupación de receptores") },
                        { title: qsTr("Transmisión local"), desc: qsTr("Streaming sin servidor externo") },
                        { title: qsTr("Sincronización multiroom"), desc: qsTr("Audio sincronizado en todas las salas") },
                        { title: qsTr("Diagnóstico de latencia"), desc: qsTr("Medición de delay en la red") },
                        { title: qsTr("Protocolo Michi Stream"), desc: qsTr("Capa de transporte del ecosistema") }
                    ]

                    GlassCard {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1))
                               / parent.columns
                        height: 80
                        title: modelData.title
                        subtitle: modelData.desc
                        variant: "base"
                    }
                }
            }
        }
    }

    Connections {
        target: root.bridge
        function onStateChanged() {
            if (!root.bridge) return
            var s = root.bridge.streamState
            if (s !== undefined) {
                root.streamState = s
                root.hasError = s === "error"
            }
        }
    }
}
