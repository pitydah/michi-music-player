import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Conversion"
    objectName: "audioConversionPage"
    focus: true
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var convBridge: typeof conversionBridge !== "undefined" ? conversionBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property int _state: 0
    property string _selectedFormat: "FLAC"
    property string _selectedCodec: "flac"
    property int _selectedBitrate: 320
    property real _selectedQuality: 5.0
    property int _selectedSampleRate: 44100
    property int _selectedBitDepth: 16
    property int _selectedChannels: 2
    property bool _keepMetadata: true
    property bool _keepArtwork: true
    property string _outputDir: ""
    property string _namingTemplate: "{artist} - {title}"
    property string _collisionPolicy: "rename"
    property string _jobId: ""
    property real _progress: 0.0
    property int _processedFiles: 0
    property int _totalFiles: 0
    property real _elapsedTime: 0.0
    property real _eta: 0.0
    property var _previewResult: null
    property string _errorMessage: ""

    readonly property int stateInputReady: 0
    readonly property int statePreviewing: 1
    readonly property int stateConverting: 2
    readonly property int stateCancelling: 3
    readonly property int stateCompleted: 4
    readonly property int stateFailed: 5

    property var _formatOptions: [
        { label: "FLAC", codec: "flac", lossless: true },
        { label: "MP3", codec: "libmp3lame", lossless: false },
        { label: "OGG Vorbis", codec: "libvorbis", lossless: false },
        { label: "Opus", codec: "libopus", lossless: false },
        { label: "WAV", codec: "pcm_s16le", lossless: true },
        { label: "AAC", codec: "aac", lossless: false },
    ]

    property var _bitrateOptions: [128, 192, 256, 320]
    property var _sampleRateOptions: [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000, 192000]
    property var _bitDepthOptions: [8, 16, 24, 32]
    property var _channelsOptions: [1, 2, 6, 8]
    property var _collisionOptions: ["overwrite", "rename", "skip"]

    Timer {
        interval: 500
        running: root._state === root.stateConverting
        repeat: true
        onTriggered: {
            root._elapsedTime += 0.5
            if (root._progress > 0 && root._processedFiles > 0) {
                var rate = root._processedFiles / Math.max(1, root._elapsedTime)
                var remaining = (root._totalFiles - root._processedFiles) / Math.max(0.001, rate)
                root._eta = remaining
            }
            if (root.convBridge) {
                var active = root.convBridge.activeJobs
                if (active.length > 0) {
                    root._progress = active[0].progress || 0
                    root._jobId = active[0].job_id || ""
                }
            }
        }
    }

    function _canConvert() {
        return root._outputDir !== "" && root._selectedFormat !== "" && root.labService !== null
    }

    function _startConversion() {
        if (!root._canConvert()) return
        if (root.convBridge && root.convBridge.outputDir) {
            root.convBridge.outputDir = root._outputDir
            root.convBridge.collisionPolicy = root._collisionPolicy
        }
        if (root.convBridge && root.convBridge.startConversion) {
            var result = root.convBridge.startConversion(root.selectedFiles && root.selectedFiles.length > 0 ? root.selectedFiles[0] : "")
            if (result && result.ok) {
                root._jobId = result.job_id || ""
                root._state = root.stateConverting
                root._progress = 0.0
                root._processedFiles = 0
                root._totalFiles = root.selectedFiles ? root.selectedFiles.length : 1
                root._elapsedTime = 0.0
                root._eta = 0.0
            } else {
                root._errorMessage = result && result.error ? result.error : "Error al iniciar conversión"
                root._state = root.stateFailed
            }
        } else {
            if (root.convBridge === null) {
                root._errorMessage = "Bridge de conversión no disponible"
                root._state = root.stateFailed
            }
        }
    }

    function _cancelConversion() {
        root._state = root.stateCancelling
        if (root.convBridge && root.convBridge.cancelJob && root._jobId) {
            root.convBridge.cancelJob(root._jobId)
        }
        root._state = root.stateInputReady
        root._progress = 0.0
        root._jobId = ""
    }

    function _retryConversion() {
        root._state = root.stateInputReady
        root._progress = 0.0
        root._jobId = ""
        root._errorMessage = ""
        root._processedFiles = 0
    }

    function _previewConversion() {
        if (!root._canConvert()) return
        root._state = root.statePreviewing
        if (root.convBridge && root.convBridge.preview && root.selectedFiles && root.selectedFiles.length > 0) {
            var filepath = typeof root.selectedFiles[0] === "string" ? root.selectedFiles[0] : root.selectedFiles[0].filepath || ""
            root._previewResult = root.convBridge.preview(filepath)
        } else {
            root._previewResult = null
        }
        root._state = root.stateInputReady
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
                text: "Conversión de audio"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Formatos: FLAC, MP3, AAC, Opus, Ogg Vorbis, WAV. Solo audio, sin video."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {
            }

            SectionHeader { text: "Formato destino"; width: parent.width; objectName: "formatHeader"; Accessible.name: "Formato destino" }

            ComboBox {
                focusPolicy: Qt.StrongFocus
                width: parent.width
                model: root._formatOptions
                textRole: "label"
                activeFocusOnTab: true
                onCurrentIndexChanged: {
                    var item = root._formatOptions[currentIndex]
                    if (item) {
                        root._selectedFormat = item.label
                        root._selectedCodec = item.codec
                    }
                }
                Component.onCompleted: currentIndex = 0
                delegate: ItemDelegate {
                    width: parent.width
                    text: label
                    highlighted: formatCombo.highlightedIndex === index
                }
            }

            SectionHeader { text: "Opciones de codificación"; width: parent.width; objectName: "codecOptionsHeader"; Accessible.name: "Opciones de codificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Text { text: "Codec: " + root._selectedCodec; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; objectName: "codecLabel" }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bitrate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._bitrateOptions
                            width: parent.width - 80
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedBitrate = root._bitrateOptions[currentIndex]
                            Component.onCompleted: currentIndex = 2
                        }
                    }

                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: "Calidad VBR (0-10): " + root._selectedQuality.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: 0; to: 10; value: root._selectedQuality; stepSize: 0.5
                            activeFocusOnTab: true
                            onMoved: root._selectedQuality = value
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Sample rate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._sampleRateOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedSampleRate = root._sampleRateOptions[currentIndex]
                            Component.onCompleted: currentIndex = 4
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bit depth:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._bitDepthOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedBitDepth = root._bitDepthOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._channelsOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedChannels = root._channelsOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                    }
                }
            }

            SectionHeader { text: "Metadatos y carátula"; width: parent.width; objectName: "metadataHeader"; Accessible.name: "Metadatos y carátula" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            checked: root._keepMetadata
                            text: "Conservar metadatos"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._keepMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            checked: root._keepArtwork
                            text: "Conservar carátula"
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._keepArtwork = checked
                        }
                    }
                }
            }

            SectionHeader { text: "Opciones de salida"; width: parent.width; objectName: "outputHeader"; Accessible.name: "Opciones de salida" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Carpeta:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        TextField {
                            focusPolicy: Qt.StrongFocus
                            width: parent.width - 160
                            text: root._outputDir
                            placeholderText: "Seleccionar carpeta de salida"
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radiusSm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._outputDir = text
                        }
                        MichiButton {
                            text: "..."; variant: "ghost"; implicitWidth: 36
                            activeFocusOnTab: true
                            Keys.onReturnPressed: onClicked()
                            Keys.onSpacePressed: onClicked()
                            onClicked: {
                                if (root.labService && root.labService.selectDirectory)
                                    root._outputDir = root.labService.selectDirectory()
                            }
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Naming:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        TextField {
                            focusPolicy: Qt.StrongFocus
                            width: parent.width - 80
                            text: root._namingTemplate
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radiusSm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._namingTemplate = text
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Colisiones:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._collisionOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._collisionPolicy = root._collisionOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                    }
                }
            }

            SectionHeader { text: "Previsualización"; width: parent.width; objectName: "previewHeader"; Accessible.name: "Previsualización" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: root._previewResult ? "accent" : "status"
                height: root._previewResult ? 100 : 60
                Text {
                    anchors.centerIn: parent
                    text: root._previewResult
                          ? "Estimado: " + (root._previewResult.estimated_size ? (root._previewResult.estimated_size / 1048576).toFixed(1) + " MB" : "desconocido")
                            + " | Espacio libre: " + (root._previewResult.free_space ? (root._previewResult.free_space / 1073741824).toFixed(1) + " GB" : "desconocido")
                          : "Selecciona archivo y perfil para previsualizar"
                    color: root._previewResult ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Previsualizar"
                    variant: "secondary"
                    enabled: root._canConvert()
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._previewConversion()
                }
                MichiButton {
                    text: root._state === root.stateConverting ? "Cancelar" : "Convertir"
                    variant: root._state === root.stateConverting ? "danger" : "primary"
                    enabled: root._state === root.stateConverting || (root._state !== root.stateCancelling && root._state !== root.stateCompleted && root._canConvert())
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (root._state === root.stateConverting || root._state === root.stateCancelling)
                            root._cancelConversion()
                        else
                            root._startConversion()
                    }
                }
                MichiButton {
                    text: "Reintentar"
                    variant: "secondary"
                    visible: root._state === root.stateFailed
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._retryConversion()
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

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                visible: root._state === root.stateConverting || root._state === root.stateCancelling || root._state === root.stateCompleted || root._state === root.stateFailed
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                    Text {
                        text: root._state === root.stateConverting ? "Convirtiendo..."
                             : root._state === root.stateCancelling ? "Cancelando..."
                             : root._state === root.stateCompleted ? "Conversión completada"
                             : root._state === root.stateFailed ? "Error: " + root._errorMessage
                             : ""
                        color: root._state === root.stateFailed ? MichiTheme.colors.error : root._state === root.stateCompleted ? MichiTheme.colors.success : MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                    }

                    MichiProgressBar {
                        width: parent.width; value: root._progress * 100; from: 0; to: 100
                        indeterminate: root._state === root.stateCancelling
                    }

                    Text {
                        text: (root._state === root.stateConverting || root._state === root.stateCompleted)
                              ? "Archivos: " + root._processedFiles + " / " + root._totalFiles
                                + " | Tiempo: " + Math.floor(root._elapsedTime) + "s"
                                + (root._eta > 0 ? " | ETA: " + Math.ceil(root._eta) + "s" : "")
                              : ""
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }

                    StatusBadge {
                        text: root._state === root.stateCompleted ? "Completado" : root._state === root.stateFailed ? "Fallido" : root._state === root.stateCancelling ? "Cancelando" : ""
                        kind: root._state === root.stateCompleted ? "success" : root._state === root.stateFailed ? "error" : "warning"
                        visible: text !== ""
                    }
                }
            }

            StatusBadge {
                visible: root.convBridge === null
                text: "Bridge de conversión no disponible"
                kind: "disconnected"
            }
        }
    }
}
