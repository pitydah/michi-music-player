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

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var convBridge: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var selectedFiles: []

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

    Component.onCompleted: root.pageState = "READY"

    Connections {
        target: root.labService
        function onJobCompleted(jobId, jobType, result) {
            if (jobId === root._jobId) {
                root._state = root.stateCompleted
                root._progress = 1.0
                root._processedFiles = root._totalFiles
            }
        }
        function onJobFailed(jobId, error) {
            if (jobId === root._jobId) {
                root._errorMessage = error
                root._state = root.stateFailed
            }
        }
    }

    property var _formatOptions: [
        { label: qsTr("FLAC"), codec: "flac", lossless: true },
        { label: qsTr("MP3"), codec: "libmp3lame", lossless: false },
        { label: qsTr("OGG Vorbis"), codec: "libvorbis", lossless: false },
        { label: qsTr("Opus"), codec: "libopus", lossless: false },
        { label: qsTr("WAV"), codec: "pcm_s16le", lossless: true },
        { label: qsTr("AAC"), codec: "aac", lossless: false },
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
        var filepath = root.selectedFiles && root.selectedFiles.length > 0 ? root.selectedFiles[0] : ""
        if (!filepath) {
            root._errorMessage = "Selecciona archivos para convertir"
            root._state = root.stateFailed
            return
        }
        var profile = {
            "format": root._selectedFormat,
            "codec": root._selectedCodec,
            "bitrate": root._selectedBitrate,
            "vbr_quality": root._selectedQuality,
            "sample_rate": root._selectedSampleRate,
            "bit_depth": root._selectedBitDepth,
            "channels": root._selectedChannels,
            "preserve_metadata": root._keepMetadata,
            "preserve_artwork": root._keepArtwork,
            "output_dir": root._outputDir,
            "filename_template": root._namingTemplate,
            "collision_policy": root._collisionPolicy
        }
        if (root.labService && root.labService.startConversion) {
            var jobId = root.labService.startConversion(filepath, JSON.stringify(profile))
            if (typeof jobId === "string" && jobId.length > 0) {
                root._jobId = jobId
                root._state = root.stateConverting
                root._progress = 0.0
                root._processedFiles = 0
                root._totalFiles = root.selectedFiles ? root.selectedFiles.length : 1
                root._elapsedTime = 0.0
                root._eta = 0.0
            } else {
                root._errorMessage = "Error al iniciar conversión"
                root._state = root.stateFailed
            }
        } else {
            root._errorMessage = "Bridge de conversión no disponible"
            root._state = root.stateFailed
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
                text: qsTr("Conversión de audio")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: qsTr("Formatos: FLAC, MP3, AAC, Opus, Ogg Vorbis, WAV. Solo audio, sin video.")
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            AudioInputSelection {
                id: inputSelection
                onFilesSelected: root.selectedFiles = filepaths
            }

            SectionHeader { text: qsTr("Formato destino"); width: parent.width; objectName: "formatHeader"; Accessible.name: "Formato destino" }

            ComboBox {
                Accessible.role: Accessible.ComboBox

                Accessible.name: "ComboBox"

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

            SectionHeader { text: qsTr("Opciones de codificación"); width: parent.width; objectName: "codecOptionsHeader"; Accessible.name: "Opciones de codificación" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Text { text: qsTr("Codec: ") + root._selectedCodec; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; objectName: "codecLabel" }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                        Text { text: qsTr("Bitrate:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._bitrateOptions
                            width: parent.width - 80
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedBitrate = root._bitrateOptions[currentIndex]
                            Component.onCompleted: currentIndex = 2
                        }
                    }
                            Accessible.role: Accessible.Slider

                            activeFocusOnTab: true


                    Column { width: parent.width; spacing: MichiTheme.spacing.xs
                        Text { text: qsTr("Calidad VBR (0-10): ") + root._selectedQuality.toFixed(1); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        MichiSlider {
                            width: parent.width
                            from: 0; to: 10; value: root._selectedQuality; stepSize: 0.5
                            activeFocusOnTab: true
                            onMoved: root._selectedQuality = value
                        }
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            activeFocusOnTab: true

                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: qsTr("Sample rate:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._sampleRateOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            onCurrentIndexChanged: root._selectedSampleRate = root._sampleRateOptions[currentIndex]
                            Component.onCompleted: currentIndex = 4
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: qsTr("Bit depth:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._bitDepthOptions
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedBitDepth = root._bitDepthOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: qsTr("Canales:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._channelsOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._selectedChannels = root._channelsOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                            Accessible.role: Accessible.CheckBox

                            Accessible.name: "CheckBox"

                            Accessible.checked: root.checked

                            activeFocusOnTab: true

                    }
                }
            }

            SectionHeader { text: qsTr("Metadatos y carátula"); width: parent.width; objectName: "metadataHeader"; Accessible.name: "Metadatos y carátula" }

            GlassMaterial {
                            Accessible.role: Accessible.CheckBox

                            Accessible.name: "CheckBox"

                            Accessible.checked: root.checked

                            activeFocusOnTab: true

                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            checked: root._keepMetadata
                            text: qsTr("Conservar metadatos")
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._keepMetadata = checked
                        }
                    }
                    Row {
                        spacing: MichiTheme.spacing.sm
                        CheckBox {
                            Accessible.role: Accessible.EditableText

                            Accessible.name: "Campo de texto"

                            checked: root._keepArtwork
                            text: qsTr("Conservar carátula")
                            activeFocusOnTab: true
                            Keys.onReturnPressed: toggle()
                            Keys.onSpacePressed: toggle()
                            onCheckedChanged: root._keepArtwork = checked
                        }
                    }
                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true

                }
            }

            SectionHeader { text: qsTr("Opciones de salida"); width: parent.width; objectName: "outputHeader"; Accessible.name: "Opciones de salida" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md
                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: qsTr("Carpeta:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        TextField {
                            Accessible.role: Accessible.EditableText

                            Accessible.name: "Campo de texto"

                            activeFocusOnTab: true

                            focusPolicy: Qt.StrongFocus
                            width: parent.width - 160
                            text: root._outputDir
                            placeholderText: qsTr("Seleccionar carpeta de salida")
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radius.sm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._outputDir = text
                        }
                        MichiButton {
                            text: qsTr("..."); variant: "ghost"; implicitWidth: 36
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

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
                        Text { text: qsTr("Naming:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 80 }
                        TextField {
                            focusPolicy: Qt.StrongFocus
                            width: parent.width - 80
                            text: root._namingTemplate
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radius.sm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._namingTemplate = text
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: qsTr("Colisiones:"); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                    Accessible.role: Accessible.Button

                            focusPolicy: Qt.StrongFocus
                            model: root._collisionOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._collisionPolicy = root._collisionOptions[currentIndex]
                            Component.onCompleted: currentIndex = 1
                        }
                    }
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                }
            }

            SectionHeader { text: qsTr("Previsualización"); width: parent.width; objectName: "previewHeader"; Accessible.name: "Previsualización" }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: root._previewResult ? "accent" : "status"
                height: root._previewResult ? 100 : 60
                Text {
                    anchors.centerIn: parent
                    text: root._previewResult
                          ? "Estimado: " + (root._previewResult.estimated_size ? (root._previewResult.estimated_size / 1048576).toFixed(1) + " MB" : "desconocido") + " | Espacio libre: " + (root._previewResult.free_space ? (root._previewResult.free_space / 1073741824).toFixed(1) + " GB" : "desconocido")
                          : "Selecciona archivo y perfil para previsualizar"
                    color: root._previewResult ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: qsTr("Previsualizar")
                    variant: "secondary"
                    enabled: root._canConvert()
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._previewConversion()
                }
                MichiButton {
                    text: root._state === root.stateConverting ? "Cancelar" : qsTr("Convertir")
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
                        Accessible.role: Accessible.ProgressBar

                        activeFocusOnTab: true

                MichiButton {
                    text: qsTr("Reintentar")
                    variant: "secondary"
                    visible: root._state === root.stateFailed
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._retryConversion()
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

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "primary"
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
                text: qsTr("Bridge de conversión no disponible")
                kind: "disconnected"
            }
        }
    }
}
