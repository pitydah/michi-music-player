import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    id: root
    objectName: "homeAudioDiagnosticsPage"
    color: MichiTheme.colors.bgApp
    focus: true

    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property var diagnostics: ({})
    property string feedback: ""
    property bool _loading: true
    readonly property string snapserverState: diagnostics.snapserver_state || "stopped"
    readonly property bool fifoExists: diagnostics.fifo_exists === true
    readonly property bool fifoWritable: diagnostics.fifo_writable === true
    readonly property int fifoSize: Number(diagnostics.fifo_size || 0)
    readonly property var activeStreams: diagnostics.active_streams || []
    readonly property var connectedReceivers: diagnostics.connected_receivers || []
    readonly property string lastError: diagnostics.last_error || ""

    signal closeRequested()

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Diagnóstico de Home Audio")

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function refreshDiagnostics() {
        root.routeEnter("home_audio.diagnostics", {})
    }

    function routeEnter(route, params) {
        root._loading = true
        if (!root.bridge) {
            root.diagnostics = ({})
            root._loading = false
            return
        }
        if (typeof root.bridge.refresh === "function")
            root.bridge.refresh()
        if (typeof root.bridge.openDiagnostics === "function")
            root.diagnostics = root.bridge.openDiagnostics()
        root._loading = false
    }

    function testTone() {
        if (!root.bridge)
            return
        var result = root.bridge.testTone()
        root.feedback = result && result.ok
                        ? qsTr("Tono de prueba iniciado.")
                        : qsTr("No se pudo iniciar el tono: %1")
                          .arg(result && result.error ? result.error : qsTr("error desconocido"))
    }

    Component.onCompleted: root.refreshDiagnostics()

    Loader {
        anchors.centerIn: parent
        active: root._loading
        sourceComponent: LoadingState { title: qsTr("Cargando diagnóstico") }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: responsive.compact
                         ? MichiTheme.spacing.md
                         : MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.md
        visible: !root._loading

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: qsTr("Diagnóstico de Home Audio")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            MichiButton {
                text: qsTr("Cerrar")
                variant: "ghost"
                onClicked: root.closeRequested()
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: Math.min(2, responsive.columnCount)
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.md

            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Snapserver")
                value: root.snapserverState
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("FIFO")
                value: root.fifoExists
                       ? (root.fifoWritable ? qsTr("Existe y es escribible")
                                            : qsTr("Existe, sin permisos de escritura"))
                       : qsTr("No existe")
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Tamaño FIFO")
                value: qsTr("%1 bytes").arg(root.fifoSize)
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Streams activos")
                value: String(root.activeStreams.length)
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Receptores conectados")
                value: String(root.connectedReceivers.length)
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Último error")
                value: root.lastError || qsTr("Ninguno")
            }
        }

        SectionHeader {
            Layout.fillWidth: true
            text: qsTr("Latencia por receptor")
        }

        Label {
            Layout.fillWidth: true
            visible: !root.diagnostics.receiver_latencies
                     || root.diagnostics.receiver_latencies.length === 0
            text: qsTr("No hay receptores conectados con datos de latencia.")
            color: MichiTheme.colors.textMuted
        }

        Repeater {
            model: root.diagnostics.receiver_latencies || []

            StatusRow {
                required property var modelData
                Layout.fillWidth: true
                label: modelData.name || modelData.id
                value: qsTr("%1 ms").arg(modelData.latency_ms || 0)
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.feedback !== ""
            text: root.feedback
            color: MichiTheme.colors.textSecondary
            wrapMode: Text.WordWrap
        }

        Item { Layout.fillHeight: true }

        GridLayout {
            Layout.fillWidth: true
            columns: responsive.compact ? 1 : 3
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.sm

            MichiButton {
                Layout.fillWidth: responsive.compact
                text: qsTr("Actualizar")
                variant: "ghost"
                onClicked: root.refreshDiagnostics()
            }

            Item {
                Layout.fillWidth: true
                visible: !responsive.compact
            }

            MichiButton {
                Layout.fillWidth: responsive.compact
                text: qsTr("Reproducir tono de prueba")
                variant: "primary"
                onClicked: root.testTone()
            }
        }
    }

    component StatusRow: Rectangle {
        required property string label
        required property string value
        implicitHeight: 56
        radius: MichiTheme.radius.md
        color: MichiTheme.colors.surfaceCard
        border.width: 1
        border.color: MichiTheme.colors.borderCard

        RowLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md

            Label {
                Layout.fillWidth: true
                text: parent.parent.label
                color: MichiTheme.colors.textSecondary
            }
            Label {
                text: parent.parent.value
                color: MichiTheme.colors.textPrimary
                font.weight: Font.DemiBold
            }
        }
    }
}
