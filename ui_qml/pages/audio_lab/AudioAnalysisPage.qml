import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string pageState: "INPUT_READY"
    property bool bridgeAvailable: root.labService !== null
    property var analysisResult: null
    property string analysisError: ""

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property int _state: 0
    property var _analysisResult: null
    property var _compareResult: null
    property string _errorMessage: ""
    property bool _compareMode: false

    objectName: "AudioAnalysisPage"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    objectName: "audioAnalysis.page"
>>>>>>> Stashed changes
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Análisis técnico"

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    function _startAnalysis() {
        if (!root.labService || !root.labService.analyzeFile) {
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
        var filepath = typeof inputSelection.selectedFiles[0] === "string"
            ? inputSelection.selectedFiles[0]
            : inputSelection.selectedFiles[0].filepath || ""
        var result = root.labService.analyzeFile(filepath)
        if (result && result.status === "unsupported") {
            root._analysisResult = null
            root._errorMessage = result.explanation || "Backend no disponible"
            root._state = root.stateFailed
        } else if (result && result.error) {
            root._analysisResult = null
            root._errorMessage = result.error
            root._state = root.stateFailed
        } else {
            root._analysisResult = result
            root._state = root.stateCompleted
        }
    }

    function _cancelAnalysis() {
        root._state = root.stateCancelling
        root._state = root.stateIdle
    }

    function _startCompare() {
        root._compareMode = !root._compareMode
    }

    Flickable {
        anchors.fill: parent
<<<<<<< Updated upstream
=======
        objectName: "audioAnalysis.focusScope"
=======
    property int _state: 0
    property var _analysisResult: null
    property var _compareResult: null
    property string _errorMessage: ""
    property bool _compareMode: false

    objectName: "AudioAnalysisPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Análisis técnico"

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateCancelling: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    function _startAnalysis() {
        if (!root.labService || !root.labService.analyzeFile) {
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
        var filepath = typeof inputSelection.selectedFiles[0] === "string"
            ? inputSelection.selectedFiles[0]
            : inputSelection.selectedFiles[0].filepath || ""
        var result = root.labService.analyzeFile(filepath)
        if (result && result.status === "unsupported") {
            root._analysisResult = null
            root._errorMessage = result.explanation || "Backend no disponible"
            root._state = root.stateFailed
        } else if (result && result.error) {
            root._analysisResult = null
            root._errorMessage = result.error
            root._state = root.stateFailed
        } else {
            root._analysisResult = result
            root._state = root.stateCompleted
        }
    }

    function _cancelAnalysis() {
        root._state = root.stateCancelling
        root._state = root.stateIdle
    }

    function _startCompare() {
        root._compareMode = !root._compareMode
    }

    Flickable {
        anchors.fill: parent
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Text {
                text: "Análisis técnico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "analysisPageTitle"
            }
            Text {
                text: "Formato, codec, bitrate, sample rate, bit depth, canales, encoder, tags, loudness, peak"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "analysisPageSubtitle"
            }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
>>>>>>> Stashed changes

            AudioInputSelection { id: inputSelection }

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "analysisActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar selección"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateCancelling && root.labService !== null && inputSelection.selectedFiles.length > 0
                    objectName: "analyzeBtn"
                    Accessible.name: "Analizar selección"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "danger"
                    visible: root._state === root.stateAnalyzing
                    objectName: "cancelAnalysisBtn"
                    Accessible.name: "Cancelar análisis"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._cancelAnalysis()
                }
                MichiButton {
                    text: root._compareMode ? "Salir de comparación" : "Comparar con otro archivo"
                    variant: "secondary"
                    objectName: "compareToggleBtn"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCompare()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "analysisBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultado del análisis"; width: parent.width; objectName: "analysisResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._state === root.stateCompleted ? "accent" : root._state === root.stateFailed ? "danger" : "base"
                objectName: "analysisResultPanel"
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
=======
            Text {
                text: "Análisis técnico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "analysisPageTitle"
            }
            Text {
                text: "Formato, codec, bitrate, sample rate, bit depth, canales, encoder, tags, loudness, peak"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "analysisPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "analysisActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar selección"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateCancelling && root.labService !== null && inputSelection.selectedFiles.length > 0
                    objectName: "analyzeBtn"
                    Accessible.name: "Analizar selección"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
<<<<<<< Updated upstream
=======
                MichiButton {
                    text: "Cancelar"
                    variant: "danger"
                    visible: root._state === root.stateAnalyzing
                    objectName: "cancelAnalysisBtn"
                    Accessible.name: "Cancelar análisis"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._cancelAnalysis()
                }
                MichiButton {
                    text: root._compareMode ? "Salir de comparación" : "Comparar con otro archivo"
                    variant: "secondary"
                    objectName: "compareToggleBtn"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCompare()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "analysisBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultado del análisis"; width: parent.width; objectName: "analysisResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._state === root.stateCompleted ? "accent" : root._state === root.stateFailed ? "danger" : "base"
                objectName: "analysisResultPanel"
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
=======
            Text {
                text: "Análisis técnico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "analysisPageTitle"
            }
            Text {
                text: "Formato, codec, bitrate, sample rate, bit depth, canales, encoder, tags, loudness, peak"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "analysisPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }

            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "analysisActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar selección"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateCancelling && root.labService !== null && inputSelection.selectedFiles.length > 0
                    objectName: "analyzeBtn"
                    Accessible.name: "Analizar selección"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
                MichiButton {
                    text: "Cancelar"
                    variant: "danger"
                    visible: root._state === root.stateAnalyzing
                    objectName: "cancelAnalysisBtn"
                    Accessible.name: "Cancelar análisis"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._cancelAnalysis()
                }
                MichiButton {
                    text: root._compareMode ? "Salir de comparación" : "Comparar con otro archivo"
                    variant: "secondary"
                    objectName: "compareToggleBtn"
                    Accessible.name: text
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startCompare()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "analysisBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultado del análisis"; width: parent.width; objectName: "analysisResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._state === root.stateCompleted ? "accent" : root._state === root.stateFailed ? "danger" : "base"
                objectName: "analysisResultPanel"
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
>>>>>>> Stashed changes
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                visible: root._state === root.stateIdle || root._state === root.stateAnalyzing
                objectName: "analysisPlaceholder"
                height: 80
                Text {
                    anchors.centerIn: parent
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Selecciona archivos para analizar"
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
                objectName: "analysisComparisonPanel"
            }

            StatusBadge {
                visible: root.labService === null
                text: "Bridge no disponible"
                kind: "disconnected"
                objectName: "analysisBridgeStatus"
                Accessible.name: "Bridge de análisis no disponible"
            }
        }
    }
}
