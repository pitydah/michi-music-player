import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Replay Gain"
    objectName: "replayGainPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property string _mode: "track"
    property real _preamp: 0.0
    property real _headroom: 0.0
    property var _results: null
    property string _errorMessage: ""

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    Component.onCompleted: root.pageState = "READY"

    function _startAnalysis() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para analizar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateAnalyzing
        root._errorMessage = ""
        if (root.labService && root.labService.previewReplayGain) {
            var filepath = typeof inputSelection.selectedFiles[0] === "string"
                ? inputSelection.selectedFiles[0]
                : inputSelection.selectedFiles[0].filepath || ""
            var result = root.labService.previewReplayGain(filepath)
            if (result && result.error) {
                root._errorMessage = result.error
                root._state = root.stateFailed
            } else {
                root._results = [result].filter(function(r) { return r !== null && r !== undefined })
                root._state = root.stateCompleted
            }
        } else {
            root._results = null
            root._state = root.stateCompleted
        }
    }

    function _applyTags() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para aplicar"
            root._state = root.stateFailed
            return
        }
        if (!root.labService || !root.labService.startReplayGain) {
            root._errorMessage = "Bridge no disponible"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateApplying
        var filepath = typeof inputSelection.selectedFiles[0] === "string"
            ? inputSelection.selectedFiles[0]
            : inputSelection.selectedFiles[0].filepath || ""
        var result = root.labService.startReplayGain(filepath, root._mode, root._preamp, root._headroom)
        if (result && result.ok) {
            root._state = root.stateCompleted
        } else {
            root._errorMessage = (result && result.error) || "Error al aplicar ReplayGain"
            root._state = root.stateFailed
        }
    }

    function _clearTags() {
        if (!root.labService || !root.labService.clearReplayGain || !inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._results = null
            root._state = root.stateIdle
            return
        }
        var filepath = typeof inputSelection.selectedFiles[0] === "string"
            ? inputSelection.selectedFiles[0]
            : inputSelection.selectedFiles[0].filepath || ""
        root.labService.clearReplayGain(filepath)
        root._results = null
        root._state = root.stateIdle
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
                text: qsTr("ReplayGain")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Análisis de loudness, pico, ganancia track/album, escritura de etiquetas")
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: qsTr("Modo de análisis"); width: parent.width; objectName: "rgModeHeader"; Accessible.name: "Modo de análisis" }

            Row {
                spacing: MichiTheme.spacing.md
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: qsTr("Track")
                    subtitle: qsTr("Ganancia por pista")
                    variant: root._mode === "track" ? "accent" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "track"
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: qsTr("Album")
                    subtitle: qsTr("Ganancia uniforme por álbum")
                    variant: root._mode === "album" ? "accent" : "base"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "album"
                }
            }

            SectionHeader { text: qsTr("Ajustes"); width: parent.width; objectName: "rgSettingsHeader"; Accessible.name: "Ajustes" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Preamp: ") + root._preamp.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            Accessible.role: Accessible.Slider

                            width: parent.width
                            from: -12; to: 12; value: root._preamp; stepSize: 0.5
                            activeFocusOnTab: true
                            onMoved: root._preamp = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Headroom: ") + root._headroom.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                            Accessible.role: Accessible.Slider

                        MichiSlider {
                            width: parent.width
                            from: 0; to: 6; value: root._headroom; stepSize: 0.5
                            activeFocusOnTab: true
                            onMoved: root._headroom = value
                        }
                    }
                }
            }

            SectionHeader { text: qsTr("Acciones"); width: parent.width; objectName: "rgActionsHeader"; Accessible.name: "Acciones" }

            Row {
                    Accessible.role: Accessible.Button

                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : qsTr("Analizar")
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateApplying && inputSelection.selectedFiles.length > 0
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    Accessible.role: Accessible.Button

                    onClicked: root._startAnalysis()
                }
                MichiButton {
                    text: qsTr("Escribir etiquetas")
                    variant: "secondary"
                    enabled: root._results !== null && root._state === root.stateCompleted
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Accessible.role: Accessible.Button

                    Keys.onSpacePressed: onClicked()
                    onClicked: root._applyTags()
                }
                MichiButton {
                    text: qsTr("Eliminar etiquetas")
                    variant: "danger"
                    enabled: inputSelection.selectedFiles.length > 0
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._clearTags()
                }
            }

            SectionHeader { text: qsTr("Resultados"); width: parent.width; objectName: "rgResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root._results ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Text {
                        text: root._state === root.stateFailed ? "Error: " + root._errorMessage
                             : root._results ? "Resultados disponibles: " + root._results.length + " archivo(s)"
                             : "Selecciona archivos para analizar ReplayGain"
                        color: root._state === root.stateFailed ? MichiTheme.colors.error : root._results ? MichiTheme.colors.success : MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                    }
                    Repeater {
                        model: root._results || []
                        Text {
                            text: modelData.filepath || modelData.file || ""
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; width: parent.width
                        }
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            StatusBadge {
                visible: root.labService === null
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: qsTr("Bridge no disponible")
                kind: "disconnected"
            }

            MichiButton {
                text: qsTr("Volver")
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { if (root.nav) root.nav.back() }
            }
        }
    }
}
