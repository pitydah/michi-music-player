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

    readonly property int stateIdle: 0
    readonly property int statePreviewing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    Component.onCompleted: {
        root.pageState = "READY"
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
                root._previewResult = {
                    integrated: result.integrated_loudness !== undefined ? result.integrated_loudness : 0,
                    peak: result.true_peak !== undefined ? result.true_peak : 0,
                    range: result.loudness_range !== undefined ? result.loudness_range : 0
                }
                root._state = root.stateCompleted
            } else {
                root._errorMessage = (result && result.error) || "Error al medir loudness"
                root._state = root.stateFailed
            }
        } else {
            root._errorMessage = "Bridge no disponible"
            root._state = root.stateFailed
        }
    }

    function _applyNormalization() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para normalizar"
            root._state = root.stateFailed
            return
        }
        var filepath = inputSelection.selectedFiles[0]
        if (!root.labService || !root.labService.startNormalization) {
            root._errorMessage = "Bridge no disponible"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateApplying
        var result = root.labService.startNormalization(filepath, "", "custom")
        if (result && result.ok) {
            root._state = root.stateCompleted
        } else if (result && result.requires_confirmation) {
            root._state = root.stateIdle
        } else {
            root._errorMessage = (result && result.error) || "Error al normalizar"
            root._state = root.stateFailed
        }
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
                text: qsTr("Normalización")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Ajuste de loudness (LUFS), pico real, umbral de puerta.")
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: qsTr("Parámetros de normalización"); width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Nivel objetivo (LUFS): ") + root._targetLufs.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width; from: -30; to: -5; value: root._targetLufs; stepSize: 0.5
                            activeFocusOnTab: true
                            onValueChanged: root._targetLufs = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Límite de pico real (dBTP): ") + root._truePeakLimit.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width; from: -6; to: 0; value: root._truePeakLimit; stepSize: 0.1
                            activeFocusOnTab: true
                            onValueChanged: root._truePeakLimit = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Umbral de puerta (dB): ") + root._gateThreshold.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width; from: -100; to: -30; value: root._gateThreshold; stepSize: 1
                            activeFocusOnTab: true
                            onValueChanged: root._gateThreshold = value
                        }
                    }
                }
            }

            SectionHeader { text: qsTr("Acciones"); width: parent.width }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("Medir loudness")
                    variant: "primary"
                    enabled: inputSelection.selectedFiles.length > 0 && root._state !== root.statePreviewing && root._state !== root.stateApplying
                    activeFocusOnTab: true
                    onClicked: root._measureLoudness()
                }
                MichiButton {
                    text: qsTr("Aplicar normalización")
                    variant: "primary"
                    enabled: root._state === root.stateCompleted && root._previewResult !== null
                    activeFocusOnTab: true
                    onClicked: root._applyNormalization()
                }
                MichiButton {
                    text: qsTr("Volver")
                    variant: "ghost"
                    activeFocusOnTab: true
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            SectionHeader { text: qsTr("Resultados"); width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md
                variant: root._state === root.stateFailed ? "danger" : "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._state === root.stateFailed ? "Error: " + root._errorMessage
                             : root._state === root.stateApplying ? "Aplicando normalización..."
                             : root._previewResult ? "LUFS integrado: " + root._previewResult.integrated.toFixed(1) + " | Pico: " + root._previewResult.peak.toFixed(1) + " dBTP | Rango: " + root._previewResult.range.toFixed(1)
                             : "Selecciona archivos para analizar"
                        color: root._state === root.stateFailed ? MichiTheme.colors.error : root._previewResult ? MichiTheme.colors.success : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            StatusBadge {
                visible: root.labService === null
                text: qsTr("Bridge no disponible")
                kind: "disconnected"
            }
        }
    }
}
