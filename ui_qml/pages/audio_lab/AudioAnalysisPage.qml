import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Analysis"
    objectName: "audioAnalysisPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property var _analysisResult: null
    property var _compareResult: null
    property string _errorMessage: ""
    property bool _compareMode: false
    property string _currentJobId: ""

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    Component.onCompleted: root.pageState = "READY"

    Connections {
        target: root.labService
        function onJobCompleted(jobId, result) {
            if (jobId === root._currentJobId) {
                root._analysisResult = result
                root._state = root.stateCompleted
            }
        }
        function onJobFailed(jobId, error) {
            if (jobId === root._currentJobId) {
                root._errorMessage = error
                root._state = root.stateFailed
            }
        }
    }

    function _startAnalysis() {
        if (!root.labService || !root.labService.startAnalysis) {
            root._errorMessage = "Servicio de análisis no disponible"
            root._state = root.stateFailed
            return
        }
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para analizar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateAnalyzing
        root._errorMessage = ""
        var filepath = inputSelection.selectedFiles[0]
        var jobId = root.labService.startAnalysis(filepath)
        if (typeof jobId === "string" && jobId.length > 0) {
            root._currentJobId = jobId
        } else {
            root._errorMessage = "Error al iniciar análisis"
            root._state = root.stateFailed
        }
    }

    function _cancelAnalysis() {
        if (root._currentJobId && root.labService && root.labService.cancelJob) {
            root._state = root.stateCancelling
            root.labService.cancelJob(root._currentJobId)
        }
        root._state = root.stateIdle
    }

    function _startCompare() {
        root._compareMode = !root._compareMode
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Análisis técnico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }
            Text {
                text: "Formato, codec, bitrate, sample rate, bit depth, canales, encoder, tags, loudness, peak"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection { id: inputSelection }

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "analysisActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    Accessible.role: Accessible.Button

                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar selección"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateCancelling && root.labService !== null && inputSelection.selectedFiles.length > 0
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
                    Accessible.role: Accessible.Button

                MichiButton {
                    text: "Cancelar"
                    variant: "danger"
                    visible: root._state === root.stateAnalyzing
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._cancelAnalysis()
                    Accessible.role: Accessible.Button

                }
                MichiButton {
                    text: root._compareMode ? "Salir de comparación" : "Comparar con otro archivo"
                    variant: "secondary"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    Accessible.role: Accessible.Button

                    onClicked: root._startCompare()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultado del análisis"; width: parent.width; objectName: "analysisResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root._state === root.stateCompleted ? "accent" : root._state === root.stateFailed ? "danger" : "base"
                visible: root._state === root.stateCompleted || root._state === root.stateFailed
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._analysisResult ? "Análisis completado" : "Error: " + root._errorMessage
                        color: root._analysisResult ? MichiTheme.colors.success : MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    }
                    Repeater {
                        model: root._analysisResult ? Object.keys(root._analysisResult) : []
                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: modelData + ": "; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; width: 140 }
                            Text { text: root._analysisResult ? String(root._analysisResult[modelData]) : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize }
                        }
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                visible: root._state === root.stateIdle || root._state === root.stateAnalyzing
                height: 80
                Text {
                    anchors.centerIn: parent
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Selecciona archivos para analizar"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            AudioTechnicalReport {
                width: parent.width
                analysisResult: root._analysisResult
            }

            AudioWaveformSummary {
                width: parent.width
                waveformData: root._analysisResult && root._analysisResult.waveform ? root._analysisResult.waveform : null
            }

            ComparisonPanel {
                width: parent.width
                visible: root._compareMode
            }

            StatusBadge {
                visible: root.labService === null
                text: "Bridge no disponible"
                kind: "disconnected"
            }
        }
    }
}
