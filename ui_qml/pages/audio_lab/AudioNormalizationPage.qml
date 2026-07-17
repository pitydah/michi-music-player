import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Normalization"
    objectName: "audioNormalizationPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property real _targetLufs: -14.0
    property real _truePeakLimit: -1.0
    property real _gateThreshold: -70.0
    property var _previewResult: null
    property string _errorMessage: ""
    property var _presets: ({})
    property string _selectedPreset: "custom"

    readonly property int stateIdle: 0
    readonly property int statePreviewing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    Component.onCompleted: {
        root.pageState = "READY"
        loadPresets()
    }

    function loadPresets() {
        if (root.labService && root.labService.getNormalizationPresets) {
            var presets = root.labService.getNormalizationPresets()
            if (presets && Object.keys(presets).length > 0) {
                root._presets = presets
                console.log("Presets cargados:", JSON.stringify(presets))
            } else {
                console.log("No se pudieron cargar los presets")
            }
        }
    }

    function applyPreset(presetKey) {
        root._selectedPreset = presetKey
        if (root.labService && root.labService.getNormalizationPreset) {
            var preset = root.labService.getNormalizationPreset(presetKey)
            if (preset && preset.ok !== false) {
                root._targetLufs = preset.target_loudness
                root._truePeakLimit = preset.true_peak_limit
                console.log("Preset aplicado:", preset.name, "- LUFS:", preset.target_loudness)
            }
        }
    }

    function _measureLoudness() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para medir"
            root._state = root.stateFailed
            return
        }
        root._state = root.statePreviewing
        var filepath = inputSelection.selectedFiles[0]
        if (root.labService && root.labService.previewNormalization) {
            var result = root.labService.previewNormalization(filepath)
            if (result && result.ok) {
                root._previewResult = result
                root._state = root.stateCompleted
            } else {
                root._errorMessage = (result && result.error) || "Error al medir loudness"
                root._state = root.stateFailed
            }
        } else {
            root._previewResult = { target: root._targetLufs, peak: root._truePeakLimit, gate: root._gateThreshold }
            root._state = root.stateCompleted
        }
    }

    function _applyNormalization() {
        root._state = root.stateApplying
        root._state = root.stateCompleted
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
                text: "Normalización"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Ajuste de loudness (LUFS), pico real, umbral de puerta. ReplayGain metadata / Player-side gain / Normalización destructiva."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Parámetros de normalización"; width: parent.width; objectName: "normParamsHeader"; Accessible.name: "Parámetros" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    // Selector de Presets
                    Column { width: parent.width; spacing: MichiTheme.spacing.sm
                        Text { 
                            text: "Preset de plataforma:"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium
                        }
                        Row {
                            spacing: MichiTheme.spacing.sm
                            wrap: true
                            Repeater {
                                model: Object.keys(root._presets)
                                delegate: MichiButton {
                                    text: root._presets[modelData] ? root._presets[modelData].name : modelData
                                    variant: root._selectedPreset === modelData ? "primary" : "ghost"
                                    enabled: root._state !== root.statePreviewing && root._state !== root.stateApplying
                                    onClicked: applyPreset(modelData)
                                    Accessible.role: Accessible.Button
                                    Keys.onReturnPressed: onClicked()
                                    Keys.onSpacePressed: onClicked()
                                }
                            }
                        }
                        Text {
                            text: root._presets[root._selectedPreset] ? root._presets[root._selectedPreset].description : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Nivel objetivo (LUFS): " + root._targetLufs.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            Accessible.role: Accessible.Slider

                            width: parent.width
                            from: -30; to: -5; value: root._targetLufs; stepSize: 0.5
                            activeFocusOnTab: true
                            onMoved: {
                                root._targetLufs = value
                                root._selectedPreset = "custom"
                            }
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Límite de pico real (dBTP): " + root._truePeakLimit.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                            Accessible.role: Accessible.Slider

                        MichiSlider {
                            width: parent.width
                            from: -6; to: 0; value: root._truePeakLimit; stepSize: 0.1
                            activeFocusOnTab: true
                            onMoved: {
                                root._truePeakLimit = value
                                root._selectedPreset = "custom"
                            }
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                            Accessible.role: Accessible.Slider

                        Text { text: "Umbral de puerta (dB): " + root._gateThreshold.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -100; to: -30; value: root._gateThreshold; stepSize: 1
                            activeFocusOnTab: true
                            onMoved: root._gateThreshold = value
                        }
                    }
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "normActionsHeader"; Accessible.name: "Acciones" }

                    Accessible.role: Accessible.Button

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Medir loudness"
                    variant: "primary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.statePreviewing && root._state !== root.stateApplying
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Accessible.role: Accessible.Button

                    Keys.onSpacePressed: onClicked()
                    onClicked: root._measureLoudness()
                }
                MichiButton {
                    text: "Aplicar"
                    variant: "primary"
                    enabled: root._state === root.stateCompleted && root._previewResult !== null
                    activeFocusOnTab: true
                    Accessible.role: Accessible.Button

                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._applyNormalization()
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

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "normResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root._previewResult ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._state === root.stateFailed ? "Error: " + root._errorMessage
                             : root._previewResult ? "LUFS objetivo: " + root._previewResult.target.toFixed(1) + " | Pico: " + root._previewResult.peak.toFixed(1) + " dBTP | Puerta: " + root._previewResult.gate.toFixed(1) + " dB"
                             : "Selecciona archivos y tipo para analizar"
                        color: root._state === root.stateFailed ? MichiTheme.colors.error : root._previewResult ? MichiTheme.colors.success : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            StatusBadge {
                visible: root.labService === null
                text: "Bridge no disponible"
                kind: "disconnected"
            }
        }
    }
}
