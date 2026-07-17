import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "audioLabOverviewPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab"

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2

    property var bridge: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var overviewData: ({})
    property int pageState: stateLoading
    property string errorMessage: ""

    function refresh() {
        root.pageState = root.stateLoading
        root.errorMessage = ""
        if (!root.bridge || typeof root.bridge.getOverviewData !== "function") {
            root.pageState = root.stateError
            root.errorMessage = "El servicio Audio Lab no está disponible."
            return
        }
        var result = root.bridge.getOverviewData()
        if (!result || result.ok === false) {
            root.pageState = root.stateError
            root.errorMessage = result && (result.detail || result.error)
                ? (result.detail || result.error)
                : "No se pudieron cargar las capacidades de Audio Lab."
            return
        }
        root.overviewData = result
        root.pageState = root.stateReady
    }

    function openArea(areaKey) {
        if (!root.bridge || typeof root.bridge.navigateToArea !== "function")
            return
        var result = root.bridge.navigateToArea(areaKey)
        if (result && result.ok === false)
            root.errorMessage = "No se pudo abrir el área solicitada."
    }

    function area(key, fallback) {
        if (root.overviewData && root.overviewData.areas && root.overviewData.areas[key])
            return root.overviewData.areas[key]
        return fallback
    }

    Component.onCompleted: root.refresh()

    Connections {
        target: root.bridge
        function onServiceAvailableChanged() { root.refresh() }
    }

    LoadingState {
        anchors.centerIn: parent
        visible: root.pageState === root.stateLoading
        title: "Cargando Audio Lab"
        subtitle: "Comprobando herramientas, dependencias y dispositivos disponibles."
    }

    ErrorState {
        anchors.centerIn: parent
        width: Math.min(480, parent.width * 0.8)
        visible: root.pageState === root.stateError
        title: "Audio Lab no está disponible"
        message: root.errorMessage
        showRetry: true
        onRetryRequested: root.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        visible: root.pageState === root.stateReady
        contentHeight: contentColumn.height + MichiTheme.spacing.xl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: contentColumn
            width: parent.width
            spacing: MichiTheme.spacing.lg

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: "Audio Lab"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Text {
                    Layout.fillWidth: true
                    text: "Herramientas para analizar, identificar, preservar y configurar audio. Las funciones físicas se habilitan únicamente cuando sus dependencias están disponibles."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                StatusBadge {
                    text: root.overviewData.dependencies && root.overviewData.dependencies.ffmpeg
                        ? "FFmpeg disponible" : "FFmpeg pendiente"
                    kind: root.overviewData.dependencies && root.overviewData.dependencies.ffmpeg
                        ? "success" : "warning"
                }
                StatusBadge {
                    text: root.overviewData.dependencies && root.overviewData.dependencies.cdparanoia
                        ? "CDParanoia disponible" : "CDParanoia pendiente"
                    kind: root.overviewData.dependencies && root.overviewData.dependencies.cdparanoia
                        ? "success" : "disconnected"
                }
                StatusBadge {
                    text: root.overviewData.active_jobs > 0
                        ? String(root.overviewData.active_jobs) + " trabajo(s) activo(s)"
                        : "Sin trabajos activos"
                    kind: root.overviewData.active_jobs > 0 ? "info" : "success"
                }
            }

            MichiBanner {
                Layout.fillWidth: true
                visible: root.errorMessage !== ""
                kind: "warning"
                message: root.errorMessage
                dismissible: true
                onDismissed: root.errorMessage = ""
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width >= 920 ? 2 : 1
                columnSpacing: MichiTheme.spacing.lg
                rowSpacing: MichiTheme.spacing.lg

                AudioLabAreaCard {
                    Layout.fillWidth: true
                    areaKey: "diagnostics"
                    title: root.area("diagnostics", { title: "Diagnóstico" }).title
                    description: root.area("diagnostics", { description: "Analiza e inspecciona archivos" }).description
                    iconText: root.area("diagnostics", { icon: "🔍" }).icon
                    status: root.area("diagnostics", { status: "unavailable" }).status
                    tools: root.area("diagnostics", { tools: [] }).tools
                    onActivated: function(key) { root.openArea(key) }
                }

                AudioLabAreaCard {
                    Layout.fillWidth: true
                    areaKey: "identifier"
                    title: root.area("identifier", { title: "Identificador de audios" }).title
                    description: root.area("identifier", { description: "Identifica y corrige metadatos" }).description
                    iconText: root.area("identifier", { icon: "🆔" }).icon
                    status: root.area("identifier", { status: "unavailable" }).status
                    tools: root.area("identifier", { tools: [] }).tools
                    onActivated: function(key) { root.openArea(key) }
                }

                AudioLabAreaCard {
                    Layout.fillWidth: true
                    areaKey: "backup"
                    title: root.area("backup", { title: "Respaldar" }).title
                    description: root.area("backup", { description: "Convierte y digitaliza audio" }).description
                    iconText: root.area("backup", { icon: "💾" }).icon
                    status: root.area("backup", { status: "unavailable" }).status
                    tools: root.area("backup", { tools: [] }).tools
                    onActivated: function(key) { root.openArea(key) }
                }

                AudioLabAreaCard {
                    Layout.fillWidth: true
                    areaKey: "output_profiles"
                    title: root.area("output_profiles", { title: "Perfiles de salida" }).title
                    description: root.area("output_profiles", { description: "Configura DAC, EQ y reproducción" }).description
                    iconText: root.area("output_profiles", { icon: "🎧" }).icon
                    status: root.area("output_profiles", { status: "unavailable" }).status
                    tools: root.area("output_profiles", { tools: [] }).tools
                    onActivated: function(key) { root.openArea(key) }
                }

                AudioLabAreaCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: root.width >= 920 ? 2 : 1
                    areaKey: "local_intelligence"
                    title: root.area("local_intelligence", { title: "Inteligencia local" }).title
                    description: root.area("local_intelligence", { description: "Análisis acústico y automatización local" }).description
                    iconText: root.area("local_intelligence", { icon: "🧠" }).icon
                    status: root.area("local_intelligence", { status: "partial" }).status
                    tools: root.area("local_intelligence", { tools: [] }).tools
                    onActivated: function(key) { root.openArea(key) }
                }
            }
        }
    }
}
