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
    property string rgMode: "auto"
    property real preamp: 0.0
    property real headroom: 6.0
    property var rgResult: null
    property string rgError: ""

<<<<<<< Updated upstream
    property int _state: 0
    property string _mode: "track"
    property real _preamp: 0.0
    property real _headroom: 0.0
    property var _results: null
    property string _errorMessage: ""

    objectName: "ReplayGainPage"
=======
<<<<<<< HEAD
    objectName: "replayGain.page"
>>>>>>> Stashed changes
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "ReplayGain"

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    function _startAnalysis() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para analizar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateAnalyzing
        root._errorMessage = ""
        if (root.labService && root.labService.analyzeFile) {
            var filepath = typeof inputSelection.selectedFiles[0] === "string"
                ? inputSelection.selectedFiles[0]
                : inputSelection.selectedFiles[0].filepath || ""
            var result = root.labService.analyzeFile(filepath)
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
        root._state = root.stateApplying
        root._state = root.stateCompleted
    }

    function _clearTags() {
        root._results = null
        root._state = root.stateIdle
    }

    Flickable {
        anchors.fill: parent
<<<<<<< Updated upstream
=======
        objectName: "replayGain.focusScope"
=======
    property int _state: 0
    property string _mode: "track"
    property real _preamp: 0.0
    property real _headroom: 0.0
    property var _results: null
    property string _errorMessage: ""

    objectName: "ReplayGainPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "ReplayGain"

    readonly property int stateIdle: 0
    readonly property int stateAnalyzing: 1
    readonly property int stateApplying: 2
    readonly property int stateCompleted: 3
    readonly property int stateFailed: 4

    function _startAnalysis() {
        if (!inputSelection.selectedFiles || inputSelection.selectedFiles.length === 0) {
            root._errorMessage = "Selecciona archivos para analizar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateAnalyzing
        root._errorMessage = ""
        if (root.labService && root.labService.analyzeFile) {
            var filepath = typeof inputSelection.selectedFiles[0] === "string"
                ? inputSelection.selectedFiles[0]
                : inputSelection.selectedFiles[0].filepath || ""
            var result = root.labService.analyzeFile(filepath)
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
        root._state = root.stateApplying
        root._state = root.stateCompleted
    }

    function _clearTags() {
        root._results = null
        root._state = root.stateIdle
    }

    Flickable {
        anchors.fill: parent
>>>>>>> Stashed changes
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

<<<<<<< Updated upstream
            Text {
                text: "ReplayGain"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "replaygainPageTitle"
            }
=======
<<<<<<< HEAD
        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
>>>>>>> Stashed changes

            Text {
                text: "Análisis de loudness, pico, ganancia track/album, escritura de etiquetas"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "replaygainPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Modo de análisis"; width: parent.width; objectName: "rgModeHeader"; Accessible.name: "Modo de análisis" }

            Row {
                spacing: MichiTheme.spacing.md
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Track"
                    subtitle: "Ganancia por pista"
                    variant: root._mode === "track" ? "accent" : "base"
                    objectName: "rgModeTrack"
                    Accessible.name: "Modo Track"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "track"
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Album"
                    subtitle: "Ganancia uniforme por álbum"
                    variant: root._mode === "album" ? "accent" : "base"
                    objectName: "rgModeAlbum"
                    Accessible.name: "Modo Album"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "album"
                }
            }

            SectionHeader { text: "Ajustes"; width: parent.width; objectName: "rgSettingsHeader"; Accessible.name: "Ajustes" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "rgSettingsPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Preamp: " + root._preamp.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -12; to: 12; value: root._preamp; stepSize: 0.5
                            objectName: "rgPreampSlider"
                            Accessible.name: "Preamp"
                            activeFocusOnTab: true
                            onMoved: root._preamp = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Headroom: " + root._headroom.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: 0; to: 6; value: root._headroom; stepSize: 0.5
                            objectName: "rgHeadroomSlider"
                            Accessible.name: "Headroom"
                            activeFocusOnTab: true
                            onMoved: root._headroom = value
                        }
                    }
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "rgActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateApplying && inputSelection.selectedFiles.length > 0
                    objectName: "rgAnalyzeBtn"
                    Accessible.name: "Analizar ReplayGain"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
<<<<<<< Updated upstream
=======
=======
            Text {
                text: "ReplayGain"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "replaygainPageTitle"
            }

            Text {
                text: "Análisis de loudness, pico, ganancia track/album, escritura de etiquetas"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "replaygainPageSubtitle"
            }

            AudioInputSelection { id: inputSelection }
            AudioSelectionSummary { width: parent.width }

            SectionHeader { text: "Modo de análisis"; width: parent.width; objectName: "rgModeHeader"; Accessible.name: "Modo de análisis" }

            Row {
                spacing: MichiTheme.spacing.md
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Track"
                    subtitle: "Ganancia por pista"
                    variant: root._mode === "track" ? "accent" : "base"
                    objectName: "rgModeTrack"
                    Accessible.name: "Modo Track"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "track"
                }
                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 70
                    title: "Album"
                    subtitle: "Ganancia uniforme por álbum"
                    variant: root._mode === "album" ? "accent" : "base"
                    objectName: "rgModeAlbum"
                    Accessible.name: "Modo Album"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._mode = "album"
                }
            }

            SectionHeader { text: "Ajustes"; width: parent.width; objectName: "rgSettingsHeader"; Accessible.name: "Ajustes" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "rgSettingsPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Preamp: " + root._preamp.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: -12; to: 12; value: root._preamp; stepSize: 0.5
                            objectName: "rgPreampSlider"
                            Accessible.name: "Preamp"
                            activeFocusOnTab: true
                            onMoved: root._preamp = value
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Headroom: " + root._headroom.toFixed(1) + " dB"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: 0; to: 6; value: root._headroom; stepSize: 0.5
                            objectName: "rgHeadroomSlider"
                            Accessible.name: "Headroom"
                            activeFocusOnTab: true
                            onMoved: root._headroom = value
                        }
                    }
                }
            }

            SectionHeader { text: "Acciones"; width: parent.width; objectName: "rgActionsHeader"; Accessible.name: "Acciones" }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: root._state === root.stateAnalyzing ? "Analizando..." : "Analizar"
                    variant: "primary"
                    enabled: root._state !== root.stateAnalyzing && root._state !== root.stateApplying && inputSelection.selectedFiles.length > 0
                    objectName: "rgAnalyzeBtn"
                    Accessible.name: "Analizar ReplayGain"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startAnalysis()
                }
>>>>>>> Stashed changes
                MichiButton {
                    text: "Escribir etiquetas"
                    variant: "secondary"
                    enabled: root._results !== null && root._state === root.stateCompleted
                    objectName: "rgApplyBtn"
                    Accessible.name: "Escribir etiquetas ReplayGain"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._applyTags()
                }
                MichiButton {
                    text: "Eliminar etiquetas"
                    variant: "danger"
                    enabled: inputSelection.selectedFiles.length > 0
                    objectName: "rgClearBtn"
                    Accessible.name: "Eliminar etiquetas ReplayGain"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._clearTags()
                }
            }

            SectionHeader { text: "Resultados"; width: parent.width; objectName: "rgResultsHeader"; Accessible.name: "Resultados" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._results ? "accent" : root._state === root.stateFailed ? "danger" : "status"
                objectName: "rgResultsPanel"
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
                text: "Bridge no disponible"
                kind: "disconnected"
                objectName: "rgBridgeStatus"
                Accessible.name: "Bridge no disponible"
            }

            MichiButton {
                text: "Volver"
                variant: "ghost"
                objectName: "rgBackBtn"
                Accessible.name: "Volver"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: { if (root.nav) root.nav.back() }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }
}
