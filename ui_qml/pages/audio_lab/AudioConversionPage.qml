import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "audioConversionPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Conversión de audio"

    readonly property int stateIdle: 0
    readonly property int statePreviewing: 1
    readonly property int stateConverting: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4
    readonly property int stateCancelling: 5

    property var bridge: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property int operationState: stateIdle
    property string selectedFormat: "flac"
    property string jobId: ""
    property var previewResult: null
    property string errorMessage: ""
    property real progress: 0.0

    readonly property var selectedFiles: inputSelection.selectedFiles || []
    readonly property string selectedFile: {
        if (!selectedFiles || selectedFiles.length === 0)
            return ""
        var first = selectedFiles[0]
        return typeof first === "string" ? first : (first.filepath || first.path || "")
    }

    function resetOperation() {
        root.operationState = root.stateIdle
        root.jobId = ""
        root.progress = 0.0
        root.errorMessage = ""
    }

    function previewConversion() {
        if (!root.bridge || root.selectedFile === "")
            return
        root.operationState = root.statePreviewing
        root.errorMessage = ""
        var result = root.bridge.previewConversion(root.selectedFile, root.selectedFormat)
        root.previewResult = result
        if (!result || result.ok === false) {
            root.errorMessage = result && (result.detail || result.error)
                ? (result.detail || result.error)
                : "No se pudo previsualizar la conversión."
            root.operationState = root.stateFailed
        } else {
            root.operationState = root.stateIdle
        }
    }

    function startConversion() {
        if (!root.bridge || root.selectedFile === "")
            return
        root.errorMessage = ""
        var result = root.bridge.startConversion(root.selectedFile, root.selectedFormat)
        if (result && result.ok) {
            root.jobId = result.job_id || ""
            root.operationState = root.stateConverting
            root.progress = 0.0
        } else {
            root.errorMessage = result && (result.detail || result.error)
                ? (result.detail || result.error)
                : "No se pudo iniciar la conversión."
            root.operationState = root.stateFailed
        }
    }

    function cancelConversion() {
        if (!root.bridge || root.jobId === "")
            return
        root.operationState = root.stateCancelling
        var result = root.bridge.cancelJob(root.jobId)
        if (result && result.ok) {
            root.resetOperation()
        } else {
            root.errorMessage = result && result.error ? result.error : "No se pudo cancelar el trabajo."
            root.operationState = root.stateFailed
        }
    }

    Connections {
        target: root.bridge

        function onJobProgress(jobId, jobType, value) {
            if (jobId === root.jobId && jobType === "conversion")
                root.progress = Math.max(0, Math.min(1, value))
        }

        function onJobCompleted(jobId, jobType, result) {
            if (jobId !== root.jobId || jobType !== "conversion")
                return
            root.progress = 1.0
            root.operationState = root.stateCompleted
            root.previewResult = result
        }

        function onJobFailed(jobId, error) {
            if (jobId !== root.jobId)
                return
            root.errorMessage = error
            root.operationState = root.stateFailed
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
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
                    text: "Conversión de audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Text {
                    Layout.fillWidth: true
                    text: "Convierte un archivo de audio con FFmpeg. La salida se crea junto al archivo original; las opciones avanzadas se habilitarán cuando el servicio pueda aplicarlas de extremo a extremo."
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }
            }

            AudioInputSelection {
                id: inputSelection
                Layout.fillWidth: true
            }

            GlassMaterial {
                Layout.fillWidth: true
                implicitHeight: formatColumn.implicitHeight + MichiTheme.spacing.lg * 2
                variant: "base"

                ColumnLayout {
                    id: formatColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        Layout.fillWidth: true
                        text: "Formato de destino"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    ComboBox {
                        id: formatCombo
                        Layout.fillWidth: true
                        model: [
                            { label: "FLAC", value: "flac" },
                            { label: "WAV", value: "wav" },
                            { label: "MP3", value: "mp3" },
                            { label: "AAC", value: "aac" },
                            { label: "Opus", value: "opus" },
                            { label: "Ogg Vorbis", value: "vorbis" },
                            { label: "ALAC", value: "alac" }
                        ]
                        textRole: "label"
                        Accessible.name: "Formato de destino"
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && model[currentIndex])
                                root.selectedFormat = model[currentIndex].value
                            root.previewResult = null
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.selectedFile !== ""
                            ? "Origen: " + root.selectedFile
                            : "Selecciona un archivo para continuar."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideMiddle
                    }
                }
            }

            GlassMaterial {
                Layout.fillWidth: true
                implicitHeight: previewColumn.implicitHeight + MichiTheme.spacing.lg * 2
                variant: root.previewResult && root.previewResult.ok ? "accent" : "status"

                ColumnLayout {
                    id: previewColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.xs

                    Text {
                        Layout.fillWidth: true
                        text: "Previsualización"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: {
                            if (!root.previewResult)
                                return "Comprueba el destino estimado antes de convertir."
                            if (root.previewResult.ok === false)
                                return root.previewResult.error || "Previsualización no disponible."
                            var size = Number(root.previewResult.estimated_size || 0)
                            return "Destino: " + String(root.previewResult.target || "")
                                + (size > 0 ? " · Tamaño estimado: " + (size / 1048576).toFixed(1) + " MB" : "")
                                + (root.previewResult.collision ? " · El archivo ya existe" : "")
                        }
                        color: root.previewResult && root.previewResult.ok === false
                            ? MichiTheme.colors.error
                            : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                    }
                }
            }

            MichiBanner {
                Layout.fillWidth: true
                visible: root.errorMessage !== ""
                kind: "error"
                message: root.errorMessage
                dismissible: true
                onDismissed: root.errorMessage = ""
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: "Previsualizar"
                    variant: "secondary"
                    enabled: root.bridge !== null
                        && root.selectedFile !== ""
                        && root.operationState !== root.stateConverting
                    onClicked: root.previewConversion()
                }

                MichiButton {
                    text: root.operationState === root.stateConverting ? "Convirtiendo…" : "Convertir"
                    variant: "primary"
                    enabled: root.bridge !== null
                        && root.selectedFile !== ""
                        && root.operationState !== root.stateConverting
                        && root.operationState !== root.stateCancelling
                    onClicked: root.startConversion()
                }

                MichiButton {
                    text: "Cancelar"
                    variant: "danger"
                    visible: root.operationState === root.stateConverting
                        || root.operationState === root.stateCancelling
                    enabled: root.operationState === root.stateConverting
                    onClicked: root.cancelConversion()
                }

                MichiButton {
                    text: "Reiniciar"
                    variant: "ghost"
                    visible: root.operationState === root.stateCompleted
                        || root.operationState === root.stateFailed
                    onClicked: root.resetOperation()
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    onClicked: {
                        if (root.nav)
                            root.nav.back()
                    }
                }
            }

            GlassMaterial {
                Layout.fillWidth: true
                implicitHeight: progressColumn.implicitHeight + MichiTheme.spacing.lg * 2
                visible: root.operationState === root.stateConverting
                    || root.operationState === root.stateCancelling
                    || root.operationState === root.stateCompleted
                variant: root.operationState === root.stateCompleted ? "accent" : "status"

                ColumnLayout {
                    id: progressColumn
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        Layout.fillWidth: true
                        text: root.operationState === root.stateCompleted
                            ? "Conversión completada"
                            : root.operationState === root.stateCancelling
                                ? "Cancelando trabajo…"
                                : "Conversión en curso"
                        color: root.operationState === root.stateCompleted
                            ? MichiTheme.colors.success
                            : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    MichiProgressBar {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: root.progress * 100
                        indeterminate: root.operationState === root.stateConverting
                            && root.progress <= 0
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.jobId !== "" ? "Trabajo: " + root.jobId : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideMiddle
                    }
                }
            }

            StatusBadge {
                visible: root.bridge === null
                text: "Bridge de conversión no disponible"
                kind: "disconnected"
            }
        }
    }
}
