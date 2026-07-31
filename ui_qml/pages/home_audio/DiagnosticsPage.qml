import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
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
    property var measuredLatencies: ({})
    property bool _loading: true
    readonly property string snapserverState: diagnostics.snapserver_state || "stopped"
    readonly property bool fifoExists: diagnostics.fifo_exists === true
    readonly property bool fifoWritable: diagnostics.fifo_writable === true
    readonly property int fifoSize: Number(diagnostics.fifo_size || 0)
    readonly property var activeStreams: diagnostics.active_streams || []
    readonly property var connectedReceivers: diagnostics.connected_receivers || []
    readonly property string lastError: diagnostics.last_error || ""
    readonly property int bytesWritten: Number(diagnostics.bytes_written || 0)
    readonly property real lastWriteTime: Number(diagnostics.last_write_time || 0)
    readonly property real throughput: Number(diagnostics.throughput_bytes_per_second || 0)
    readonly property var signalSteps: [
        {
            "name": qsTr("Michi"),
            "status": root.activeStreams.length > 0 ? "ok" : "warning",
            "detail": root.activeStreams.length > 0
                      ? qsTr("Michi está enviando un stream activo.")
                      : qsTr("Iniciá la reproducción para producir señal de audio.")
        },
        {
            "name": qsTr("FIFO"),
            "status": !root.fifoExists || !root.fifoWritable ? "error"
                      : (root.bytesWritten > 0 ? "ok" : "warning"),
            "detail": !root.fifoExists ? qsTr("La tubería no existe. Reiniciá la distribución.")
                      : (!root.fifoWritable ? qsTr("Michi no puede escribir. Revisá los permisos.")
                      : (root.bytesWritten > 0 ? qsTr("La FIFO recibió audio correctamente.")
                      : qsTr("La FIFO está lista, pero todavía no recibió audio.")))
        },
        {
            "name": qsTr("Snapserver"),
            "status": root.snapserverState === "running" ? "ok"
                      : (root.snapserverState === "error" ? "error" : "warning"),
            "detail": root.snapserverState === "running"
                      ? qsTr("Snapserver está procesando la señal.")
                      : qsTr("Iniciá Snapserver desde Home Audio y volvé a probar.")
        },
        {
            "name": qsTr("Receptores"),
            "status": root.connectedReceivers.length > 0 ? "ok" : "warning",
            "detail": root.connectedReceivers.length > 0
                      ? qsTr("%1 receptor(es) conectado(s).").arg(root.connectedReceivers.length)
                      : qsTr("Encendé un receptor y verificá que esté en la misma red.")
        }
    ]

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
        if (result && result.ok)
            root.refreshDiagnostics()
    }

    function measureReceiver(receiverId) {
        if (!root.bridge || typeof root.bridge.measureLatency !== "function")
            return
        var result = root.bridge.measureLatency(receiverId)
        if (!result || !result.ok) {
            root.feedback = qsTr("No se pudo medir la latencia: %1")
                            .arg(result && result.error ? result.error : qsTr("error desconocido"))
            return
        }
        var updated = Object.assign({}, root.measuredLatencies)
        updated[receiverId] = result
        root.measuredLatencies = updated
        root.feedback = qsTr("Latencia actualizada para %1.").arg(result.receiver_name)
    }

    function diagnosticsReport() {
        var lines = [
            qsTr("Diagnóstico de Home Audio"),
            new Date().toISOString(),
            "",
            qsTr("Ruta de señal: Michi → FIFO → Snapserver → Receptores")
        ]
        for (var index = 0; index < root.signalSteps.length; ++index) {
            var step = root.signalSteps[index]
            lines.push(step.name + ": " + step.status + " — " + step.detail)
        }
        lines.push("", qsTr("Bytes escritos: %1").arg(root.bytesWritten))
        lines.push(qsTr("Rendimiento: %1 KiB/s").arg((root.throughput / 1024).toFixed(1)))
        lines.push(qsTr("Última escritura: %1").arg(root.lastWriteTime || qsTr("Sin datos")))
        lines.push(qsTr("Último error: %1").arg(root.lastError || qsTr("Ninguno")))
        return lines.join("\n")
    }

    function copyDiagnostics() {
        var result = root.bridge && typeof root.bridge.copyDiagnostics === "function"
                     ? root.bridge.copyDiagnostics(root.diagnosticsReport()) : null
        root.feedback = result && result.ok
                        ? qsTr("Diagnóstico copiado al portapapeles.")
                        : qsTr("No se pudo copiar el diagnóstico.")
    }

    Component.onCompleted: root.refreshDiagnostics()

    FileDialog {
        id: exportDialog
        title: qsTr("Exportar diagnóstico de Home Audio")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "txt"
        nameFilters: [qsTr("Informe de texto (*.txt)")]
        onAccepted: {
            var result = root.bridge.exportDiagnostics(selectedFile.toString(),
                                                         root.diagnosticsReport())
            root.feedback = result && result.ok
                            ? qsTr("Informe exportado correctamente.")
                            : qsTr("No se pudo exportar el informe: %1")
                              .arg(result && result.error ? result.error : qsTr("error desconocido"))
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root._loading
        sourceComponent: MichiLoadingState { title: qsTr("Cargando diagnóstico") }
    }

    ScrollView {
        id: diagnosticsScroll
        anchors.fill: parent
        visible: !root._loading
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            readonly property real pageMargin: responsive.compact
                                               ? MichiTheme.spacing.md
                                               : MichiTheme.spacing.xl
            x: pageMargin
            width: diagnosticsScroll.availableWidth - (pageMargin * 2)
            spacing: MichiTheme.spacing.md

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

        SectionHeader {
            Layout.fillWidth: true
            text: qsTr("Ruta de señal · Michi → FIFO → Snapserver → Receptores")
        }

        GridLayout {
            Layout.fillWidth: true
            columns: responsive.compact ? 1 : 4
            columnSpacing: MichiTheme.spacing.sm
            rowSpacing: MichiTheme.spacing.sm

            Repeater {
                model: root.signalSteps

                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.minimumHeight: 104
                    radius: MichiTheme.radius.md
                    color: modelData.status === "ok" ? MichiTheme.colors.successSurface
                           : (modelData.status === "error" ? MichiTheme.colors.errorSurface
                           : MichiTheme.colors.warningSurface)
                    border.width: 1
                    border.color: modelData.status === "ok" ? MichiTheme.colors.successBorder
                                  : (modelData.status === "error" ? MichiTheme.colors.errorBorder
                                  : MichiTheme.colors.warningBorder)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.xs

                        Label {
                            Layout.fillWidth: true
                            text: (parent.parent.modelData.status === "ok" ? qsTr("Correcto · ")
                                   : (parent.parent.modelData.status === "error" ? qsTr("Error · ")
                                   : qsTr("Atención · "))) + parent.parent.modelData.name
                            color: parent.parent.modelData.status === "ok" ? MichiTheme.colors.success
                                   : (parent.parent.modelData.status === "error" ? MichiTheme.colors.error
                                   : MichiTheme.colors.warning)
                            font.weight: Font.DemiBold
                        }
                        Label {
                            Layout.fillWidth: true
                            text: parent.parent.modelData.detail
                            color: MichiTheme.colors.textSecondary
                            wrapMode: Text.WordWrap
                        }
                    }
                }
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
                label: qsTr("Bytes escritos en FIFO")
                value: String(root.bytesWritten)
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Rendimiento FIFO")
                value: qsTr("%1 KiB/s").arg((root.throughput / 1024).toFixed(1))
            }
            StatusRow {
                Layout.fillWidth: true
                label: qsTr("Última escritura FIFO")
                value: root.lastWriteTime > 0
                       ? new Date(root.lastWriteTime * 1000).toLocaleTimeString()
                       : qsTr("Sin datos")
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

            Rectangle {
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 64
                radius: MichiTheme.radius.md
                color: MichiTheme.colors.surfaceCard
                border.width: 1
                border.color: MichiTheme.colors.borderCard

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.md

                    Label {
                        Layout.fillWidth: true
                        text: parent.parent.modelData.name || parent.parent.modelData.id
                        color: MichiTheme.colors.textSecondary
                    }
                    Label {
                        property var measured: root.measuredLatencies[parent.parent.modelData.id]
                        text: measured
                              ? qsTr("%1 ms · control %2 ms")
                                .arg(measured.latency_ms).arg(measured.control_rtt_ms)
                              : qsTr("%1 ms reportados").arg(parent.parent.modelData.latency_ms || 0)
                        color: MichiTheme.colors.textPrimary
                    }
                    MichiButton {
                        text: qsTr("Medir")
                        variant: "ghost"
                        onClicked: root.measureReceiver(parent.parent.modelData.id)
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.feedback !== ""
            text: root.feedback
            color: MichiTheme.colors.textSecondary
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: responsive.compact ? 1 : 5
            columnSpacing: MichiTheme.spacing.md
            rowSpacing: MichiTheme.spacing.sm

            MichiButton {
                Layout.fillWidth: responsive.compact
                text: qsTr("Actualizar")
                variant: "ghost"
                onClicked: root.refreshDiagnostics()
            }

            MichiButton {
                Layout.fillWidth: responsive.compact
                text: qsTr("Copiar diagnóstico")
                variant: "ghost"
                onClicked: root.copyDiagnostics()
            }

            MichiButton {
                Layout.fillWidth: responsive.compact
                text: qsTr("Exportar informe")
                variant: "ghost"
                onClicked: exportDialog.open()
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
