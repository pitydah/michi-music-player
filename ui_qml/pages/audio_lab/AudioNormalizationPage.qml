import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property real _targetLufs: -14.0
    property real _truePeakLimit: -1.0
    property real _gateThreshold: -70.0
    property var _previewResult: null
    property string _errorMessage: ""

    objectName: "AudioNormalizationPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Normalización"

    readonly property int stateIdle: 0
    readonly property int statePreviewing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    function _measureLoudness() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para medir"
            root._state = root.stateFailed
            return
        }
        root._state = root.statePreviewing
        root._previewResult = { target: root._targetLufs, peak: root._truePeakLimit, gate: root._gateThreshold }
        root._state = root.stateCompleted
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
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Normalización"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "normPageTitle"
            }

            Text {
                text: "Ajuste de loudness (LUFS), pico real, umbral de puerta. ReplayGain metadata / Player-side gain / Normalización destructiva."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "normPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Parámetros de normalización"; width: parent.width; objectName: "normParamsHeader"; Accessible.name: "Parámetros" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "normParamsPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Nivel objetivo (LUFS): " + root._targetLufs.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -30; to: -5; value: root._targetLufs; stepSize: 0.5
                            objectName: "normTargetSlider"
                            Accessible.name: "Nivel objetivo LUFS"
                            activeFocusOnTab: true
                            onMoved: root._targetLufs = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Límite de pico real (dBTP): " + root._truePeakLimit.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -6; to: 0; value: root._truePeakLimit; stepSize: 0.1
                            objectName: "normPeakSlider"
                            Accessible.name: "Límite de pico real"
                            activeFocusOnTab: true
                            onMoved: root._truePeakLimit = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Umbral de puerta (dB): " + root._gateThreshold.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -100; to: -30; value: root._gateThreshold; stepSize: 1
                            objectName: "normGateSlider"
                            Accessible.name: "Umbral de puerta"
                            activeFocusOnTab: true
                            onMoved: root._gateThreshold = value
                        }
                    }
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "normActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Medir loudness"
                    variant: "primary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.statePreviewing && root._state !== root.stateApplying
                    objectName: "normMeasureBtn"
                    Accessible.name: "Medir loudness"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._measureLoudness()
                }
                MichiButton {
                    text: "Aplicar"
                    variant: "primary"
                    enabled: root._state === root.stateCompleted && root._previewResult !== null
                    objectName: "normApplyBtn"
                    Accessible.name: "Aplicar normalización"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._applyNormalization()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "normBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "normResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._previewResult ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                objectName: "normResultsPanel"
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
                objectName: "normBridgeStatus"
                Accessible.name: "Bridge no disponible"
            }
        }
    }
}
