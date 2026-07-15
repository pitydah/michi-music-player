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
    property string fileA: ""
    property string fileB: ""
    property var comparisonResult: null
    property string comparisonError: ""

    property int _state: 0
    property var _fileA: null
    property var _fileB: null
    property var _comparisonResult: null
    property string _errorMessage: ""

    objectName: "AudioComparisonPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Comparación de audio"

    readonly property int stateIdle: 0
    readonly property int stateComparing: 1
    readonly property int stateCompleted: 2
    readonly property int stateFailed: 3

    function _startComparison() {
        if (!root._fileA || !root._fileB) {
            root._errorMessage = "Selecciona dos archivos para comparar"
            root._state = root.stateFailed
            return
        }
        root._state = root.stateComparing
        root._errorMessage = ""
        var pathA = typeof root._fileA === "string" ? root._fileA : root._fileA.filepath || ""
        var pathB = typeof root._fileB === "string" ? root._fileB : root._fileB.filepath || ""
        if (root.labService && root.labService.compareFiles) {
            root._comparisonResult = root.labService.compareFiles(pathA, pathB)
        } else {
            root._comparisonResult = {
                file_a: pathA, file_b: pathB,
                identical: false,
                dimensions: [
                    { key: "format", label: "Formato", identical: false },
                    { key: "bitrate", label: "Bitrate", identical: false },
                    { key: "sample_rate", label: "Sample Rate", identical: false },
                    { key: "bit_depth", label: "Bit Depth", identical: false },
                    { key: "channels", label: "Canales", identical: false },
                    { key: "size", label: "Tamaño", identical: false },
                ]
            }
        }
        root._state = root.stateCompleted
    }

    function _swapFiles() {
        var tmp = root._fileA
        root._fileA = root._fileB
        root._fileB = tmp
        root._comparisonResult = null
        root._state = root.stateIdle
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

            Text {
                text: "Comparación de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "comparisonPageTitle"
            }

            Text {
                text: "Compara variantes por formato, codec, bitrate, sample rate, bit depth, canales, tamaño, loudness, pico"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "comparisonPageSubtitle"
            }

            SectionHeader { text: "Archivo A"; width: parent.width; objectName: "fileAHeader"; Accessible.name: "Archivo A" }

            AudioInputSelection {
                id: inputSelectionA
                objectName: "comparisonInputA"
                onFilesSelected: { root._fileA = filepaths && filepaths.length > 0 ? filepaths[0] : null; root._comparisonResult = null; root._state = root.stateIdle }
            }

            SectionHeader { text: "Archivo B"; width: parent.width; objectName: "fileBHeader"; Accessible.name: "Archivo B" }

            AudioInputSelection {
                id: inputSelectionB
                objectName: "comparisonInputB"
                onFilesSelected: { root._fileB = filepaths && filepaths.length > 0 ? filepaths[0] : null; root._comparisonResult = null; root._state = root.stateIdle }
            }

            SectionHeader { text: "Dimensiones de comparación"; width: parent.width; objectName: "comparisonDimsHeader"; Accessible.name: "Dimensiones" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._comparisonResult ? "accent" : "base"
                objectName: "comparisonDimsPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Repeater {
                        model: root._comparisonResult && root._comparisonResult.dimensions
                               ? root._comparisonResult.dimensions
                               : [
                                   { label: "Formato", identical: false }, { label: "Codec", identical: false },
                                   { label: "Bitrate", identical: false }, { label: "Sample Rate", identical: false },
                                   { label: "Bit Depth", identical: false }, { label: "Canales", identical: false },
                                   { label: "Tamaño", identical: false }, { label: "Loudness", identical: false },
                                   { label: "Peak", identical: false }, { label: "Metadata", identical: false },
                                   { label: "Hash", identical: false }, { label: "Integridad", identical: false },
                               ]
                        Row {
                            spacing: MichiTheme.spacing.sm; height: 28
                            Text { text: modelData.label || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: 120; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root._comparisonResult ? (modelData.identical ? "✓ Igual" : "✗ Diferente") : "—"; color: modelData.identical ? MichiTheme.colors.success : root._comparisonResult ? MichiTheme.colors.error : MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 100; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root._comparisonResult ? "vs" : ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize; width: 30; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root._comparisonResult ? (modelData.identical ? "" : "Diferente") : ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; width: 100; elide: Text.ElideRight }
                        }
                    }
                }
                height: childrenRect.height + MichiTheme.spacing.lg * 2
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Comparar"
                    variant: "primary"
                    enabled: root._fileA !== null && root._fileB !== null && root._state !== root.stateComparing
                    objectName: "compareBtn"
                    Accessible.name: "Comparar archivos"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._startComparison()
                }
                MichiButton {
                    text: "Intercambiar A/B"
                    variant: "secondary"
                    enabled: root._fileA !== null && root._fileB !== null
                    objectName: "swapABBtn"
                    Accessible.name: "Intercambiar archivos A y B"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._swapFiles()
                }
                MichiButton {
                    text: "Volver"
                    variant: "ghost"
                    objectName: "comparisonBackBtn"
                    Accessible.name: "Volver"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: { if (root.nav) root.nav.back() }
                }
            }

            StatusBadge {
                visible: root.labService === null
                text: "Bridge no disponible"
                kind: "disconnected"
                objectName: "comparisonBridgeStatus"
                Accessible.name: "Bridge no disponible"
            }
        }
    }
}
