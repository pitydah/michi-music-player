import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var convBridge: typeof conversionBridge !== "undefined" ? conversionBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property string pageState: "INPUT_READY"
    property bool bridgeAvailable: root.labService !== null
    property string jobId: ""
    property real convProgress: 0.0
    property var previewData: null
    property string convError: ""

    property var formatModel: ["FLAC", "MP3", "OGG", "Opus", "WAV", "AAC"]
    property var codecModel: {"FLAC":"flac","MP3":"libmp3lame","OGG":"libvorbis","Opus":"libopus","WAV":"pcm_s16le","AAC":"aac"}
    property var sampleRateModel: ["8000","11025","16000","22050","44100","48000","96000","192000"]
    property var bitDepthModel: ["8","16","24","32"]
    property var channelsModel: ["1","2","6","8"]
    property var collisionModel: ["rename","overwrite","skip","ask"]

    property string selectedFormat: "FLAC"
    property string selectedCodec: "flac"
    property real qualityVbr: 5.0
    property string selectedSampleRate: "44100"
    property string selectedBitDepth: "16"
    property string selectedChannels: "2"
    property bool keepMetadata: true
    property bool keepArtwork: true
    property string outputDir: ""
    property string namingTemplate: "{artist} - {title}"
    property string collisionPolicy: "rename"

    objectName: "audioConversion.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Conversión de audio"

    function startPreview() {
        if (!root.convBridge) return
        var result = root.convBridge.preview("/dummy")
        if (result && result.ok) {
            root.previewData = result
            root.pageState = "PREVIEWING"
        }
    }

    function startConvert() {
        if (!root.convBridge) return
        root.pageState = "CONVERTING"
        root.convProgress = 0.0
        root.convError = ""
        var result = root.convBridge.startConversion("/dummy")
        if (result && result.ok) {
            root.jobId = result.job_id || ""
        } else {
            root.convError = result ? (result.error || "UNKNOWN") : "NO_BRIDGE"
            root.pageState = "FAILED"
        }
    }

    function cancelConvert() {
        if (!root.convBridge || !root.jobId) return
        root.pageState = "CANCELLING"
        root.convBridge.cancelJob(root.jobId)
        root.pageState = "INPUT_READY"
        root.jobId = ""
    }

    function retryConvert() {
        if (!root.convBridge || !root.jobId) return
        root.convBridge.retryJob(root.jobId)
        root.pageState = "INPUT_READY"
        root.jobId = ""
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioConversion.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Text {
                    text: "Conversión de audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Conversión de audio"
                }

                Text {
                    text: "Formatos: FLAC, MP3, OGG, Opus, WAV, AAC. Solo audio."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                }

                SectionHeader { text: "Selección de entrada"; width: parent.width; objectName: "conversion.section.input" }
                AudioInputSelection {}

                SectionHeader { text: "Formato destino"; width: parent.width; objectName: "conversion.section.format" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                    objectName: "conversion.formatSelector"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Formato:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: formatCombo
                                objectName: "conversion.formatCombo"
                                model: root.formatModel
                                currentIndex: 0
                                Accessible.name: "Formato destino"
                                onCurrentTextChanged: {
                                    root.selectedFormat = currentText
                                    root.selectedCodec = root.codecModel[currentText] || "flac"
                                }
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Codec:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root.selectedCodec; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                        }

                        Column {
                            spacing: MichiTheme.spacing.xs
                            Text { text: "Calidad VBR (0-10): " + root.qualityVbr.toFixed(1); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                            MichiSlider {
                                id: qualitySlider
                                objectName: "conversion.qualitySlider"
                                width: parent.width
                                from: 0; to: 10; value: root.qualityVbr; stepSize: 0.5
                                accessibleName: "Calidad VBR"
                                onMoved: function(v) { root.qualityVbr = v }
                            }
                        }
                    }
                }

                SectionHeader { text: "Opciones de audio"; width: parent.width; objectName: "conversion.section.audio" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "conversion.audioOptions"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Sample rate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: sampleRateCombo
                                objectName: "conversion.sampleRateCombo"
                                model: root.sampleRateModel
                                currentIndex: 4
                                Accessible.name: "Sample rate"
                                onCurrentTextChanged: root.selectedSampleRate = currentText
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Bit depth:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: bitDepthCombo
                                objectName: "conversion.bitDepthCombo"
                                model: root.bitDepthModel
                                currentIndex: 1
                                Accessible.name: "Bit depth"
                                onCurrentTextChanged: root.selectedBitDepth = currentText
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: channelsCombo
                                objectName: "conversion.channelsCombo"
                                model: root.channelsModel
                                currentIndex: 1
                                Accessible.name: "Canales"
                                onCurrentTextChanged: root.selectedChannels = currentText
                            }
                        }
                    }
                }

                SectionHeader { text: "Metadatos y carátula"; width: parent.width; objectName: "conversion.section.metadata" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "conversion.metadataOptions"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        CheckBox {
                            id: keepMetaCheck
                            objectName: "conversion.keepMetadata"
                            checked: root.keepMetadata
                            text: "Conservar metadatos"
                            Accessible.name: "Conservar metadatos"
                            onCheckedChanged: root.keepMetadata = checked
                        }
                        CheckBox {
                            id: keepArtCheck
                            objectName: "conversion.keepArtwork"
                            checked: root.keepArtwork
                            text: "Conservar carátula"
                            Accessible.name: "Conservar carátula"
                            onCheckedChanged: root.keepArtwork = checked
                        }
                    }
                }

                SectionHeader { text: "Salida"; width: parent.width; objectName: "conversion.section.output" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "conversion.outputOptions"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Directorio:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root.outputDir || "(misma que origen)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            MichiButton { text: "Examinar"; variant: "ghost"; objectName: "conversion.browseOutput"; Accessible.name: "Examinar directorio de salida" }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Plantilla:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root.namingTemplate; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Colisiones:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: collisionCombo
                                objectName: "conversion.collisionCombo"
                                model: root.collisionModel
                                currentIndex: 0
                                Accessible.name: "Política de colisiones"
                                onCurrentTextChanged: root.collisionPolicy = currentText
                            }
                        }
                    }
                }

                SectionHeader { text: "Previsualización"; width: parent.width; objectName: "conversion.section.preview" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                    objectName: "conversion.preview"
                    height: root.previewData ? 100 : 80
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        visible: root.previewData !== null
                        Text { text: "Estimado: " + (root.previewData ? root.previewData.estimated_size : 0) + " bytes"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        Text { text: "Espacio libre: " + (root.previewData ? root.previewData.free_space : 0) + " bytes"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: root.previewData && root.previewData.free_space < root.previewData.estimated_size ? "ADVERTENCIA: espacio insuficiente" : ""; color: MichiTheme.colors.warning; font.pixelSize: MichiTheme.typography.metaSize; visible: root.previewData !== null }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "Selecciona archivo y perfil para previsualizar"
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                        visible: root.previewData === null
                    }
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: root.pageState === "FAILED" ? "danger" : (root.pageState === "CONVERTING" || root.pageState === "CANCELLING" ? "accent" : "status")
                    objectName: "conversion.status"
                    visible: root.pageState !== "INPUT_READY"
                    height: 60
                    Column {
                        anchors.centerIn: parent; spacing: MichiTheme.spacing.sm
                        Text { text: root.pageState === "CONVERTING" ? "Convirtiendo... " + Math.round(root.convProgress * 100) + "%" : root.pageState === "CANCELLING" ? "Cancelando..." : root.pageState === "COMPLETED" ? "Conversión completada" : root.pageState === "FAILED" ? "Error: " + root.convError : ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                        MichiProgressBar { width: 200; value: root.convProgress; from: 0; to: 1; visible: root.pageState === "CONVERTING" || root.pageState === "CANCELLING" }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: "Previsualizar"; variant: "secondary"
                        objectName: "conversion.previewBtn"
                        enabled: root.pageState === "INPUT_READY" || root.pageState === "PREVIEWING"
                        onClicked: root.startPreview()
                        Accessible.name: "Previsualizar conversión"
                    }
                    MichiButton {
                        text: root.pageState === "CONVERTING" ? "Cancelar" : (root.pageState === "FAILED" ? "Reintentar" : "Convertir")
                        variant: root.pageState === "CONVERTING" || root.pageState === "CANCELLING" ? "danger" : "primary"
                        objectName: root.pageState === "CONVERTING" ? "conversion.cancelBtn" : (root.pageState === "FAILED" ? "conversion.retryBtn" : "conversion.startBtn")
                        enabled: root.pageState !== "CANCELLING"
                        onClicked: {
                            if (root.pageState === "CONVERTING") root.cancelConvert()
                            else if (root.pageState === "FAILED") root.retryConvert()
                            else root.startConvert()
                        }
                        Accessible.name: root.pageState === "CONVERTING" ? "Cancelar conversión" : (root.pageState === "FAILED" ? "Reintentar conversión" : "Iniciar conversión")
                    }
                    MichiButton {
                        text: "Volver"; variant: "ghost"
                        objectName: "conversion.backBtn"
                        enabled: root.pageState !== "CONVERTING" && root.pageState !== "CANCELLING"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Volver"
                    }
                }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                    objectName: "conversion.info"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        StatusBadge { text: "Requiere ffmpeg"; kind: "info" }
                        StatusBadge { text: "Experimental"; kind: "experimental" }
                    }
                }
            }
        }
    }
}
