import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Conversion Profile Editor"
    objectName: "audioConversionProfileEditor"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null

    property bool _editing: false
    property string _profileName: ""
    property string _profileFormat: "FLAC"
    property string _profileCodec: "flac"
    property int _profileBitrate: 320
    property int _profileSampleRate: 44100
    property int _profileBitDepth: 16
    property int _profileChannels: 2
    property string _validationError: ""

    property var _formatOptions: [
        { label: "FLAC", codec: "flac", lossless: true },
        { label: "MP3", codec: "libmp3lame", lossless: false },
        { label: "OGG Vorbis", codec: "libvorbis", lossless: false },
        { label: "Opus", codec: "libopus", lossless: false },
        { label: "WAV", codec: "pcm_s16le", lossless: true },
        { label: "AAC", codec: "aac", lossless: false },
    ]

    property var _sampleRateOptions: [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000, 192000]
    property var _bitDepthOptions: [8, 16, 24, 32]
    property var _channelsOptions: [1, 2, 6, 8]
    property var _bitrateOptions: [128, 192, 256, 320]

    property var _presetProfiles: [
        { name: "Portable MP3", format: "MP3", codec: "libmp3lame", bitrate: 320, sr: 44100, depth: 16, channels: 2 },
        { name: "Portable AAC", format: "AAC", codec: "aac", bitrate: 256, sr: 44100, depth: 16, channels: 2 },
        { name: "Efficient Opus", format: "Opus", codec: "libopus", bitrate: 128, sr: 48000, depth: 16, channels: 2 },
        { name: "Lossless FLAC", format: "FLAC", codec: "flac", bitrate: 0, sr: 44100, depth: 16, channels: 2 },
        { name: "Archival FLAC", format: "FLAC", codec: "flac", bitrate: 0, sr: 192000, depth: 24, channels: 2 },
        { name: "PCM WAV", format: "WAV", codec: "pcm_s16le", bitrate: 0, sr: 44100, depth: 16, channels: 2 },
    ]

    function _isValid() {
        if (root._profileName.trim() === "") {
            root._validationError = "El nombre del perfil es obligatorio"
            return false
        }
        root._validationError = ""
        return true
    }

    function _saveProfile() {
        if (!root._isValid()) return
        root._editing = false
    }

    Component.onCompleted: root.pageState = "READY"

    function _loadProfile(preset) {
        root._profileName = preset.name
        root._profileFormat = preset.format
        root._profileCodec = preset.codec
        root._profileBitrate = preset.bitrate
        root._profileSampleRate = preset.sr
        root._profileBitDepth = preset.depth
        root._profileChannels = preset.channels
        root._editing = true
        root._validationError = ""
    }

    function _deleteProfile() {
        root._profileName = ""
        root._profileFormat = "FLAC"
        root._profileCodec = "flac"
        root._editing = false
        root._validationError = ""
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
                text: root._editing ? "Editar perfil: " + root._profileName : "Perfiles de conversión"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Portable MP3, Portable AAC, Efficient Opus, Lossless FLAC, Archival FLAC, PCM WAV"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
            }

            SectionHeader { text: "Perfiles predefinidos"; width: parent.width; objectName: "presetsHeader"; Accessible.name: "Perfiles predefinidos" }

            Repeater {
                model: root._presetProfiles

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radius.sm; variant: "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.20; text: modelData.name; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.12; text: modelData.format; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.12; text: modelData.bitrate > 0 ? modelData.bitrate + "k" : "—"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.15; text: modelData.sr + " Hz"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.10; text: modelData.depth + " bit"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        MichiButton { width: 60; height: 28; text: "Usar"; variant: "primary"; anchors.verticalCenter: parent.verticalCenter; objectName: "usePresetBtn_" + index; Accessible.name: "Usar " + modelData.name; activeFocusOnTab: true; Keys.onReturnPressed: onClicked(); Keys.onSpacePressed: onClicked(); onClicked: root._loadProfile(modelData) }
                    }
                }
            }

            SectionHeader { text: "Editor de perfil personalizado"; width: parent.width; objectName: "editorHeader"; Accessible.name: "Editor de perfil" }

            InlineError {
                message: root._validationError
                width: parent.width
                showDismiss: true
                onDismissed: root._validationError = ""
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Nombre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField {
                            Accessible.role: Accessible.EditableText

                            Accessible.name: "Campo de texto"

                            activeFocusOnTab: true

                            focusPolicy: Qt.StrongFocus
                            width: parent.width - 100; text: root._profileName
                            placeholderText: "Nombre del perfil"
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radius.sm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._profileName = text
                        }
                    }

                    Row {
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Formato:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._formatOptions
                            textRole: "label"
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: {
                                var item = root._formatOptions[currentIndex]
                                if (item) { root._profileFormat = item.label; root._profileCodec = item.codec }
                            }
                        }
                    }
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            activeFocusOnTab: true


                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bitrate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._bitrateOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            onCurrentIndexChanged: root._profileBitrate = root._bitrateOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Sample rate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._sampleRateOptions
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileSampleRate = root._sampleRateOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bit depth:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            Accessible.role: Accessible.ComboBox

                            Accessible.name: "ComboBox"

                            focusPolicy: Qt.StrongFocus
                            model: root._bitDepthOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileBitDepth = root._bitDepthOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                    Accessible.role: Accessible.Button

                        ComboBox {
                            focusPolicy: Qt.StrongFocus
                            model: root._channelsOptions
                            width: parent.width - 100
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileChannels = root._channelsOptions[currentIndex]
                        }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Guardar perfil"
                    Accessible.role: Accessible.Button

                    variant: "primary"
                    enabled: root._profileName.trim() !== ""
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._saveProfile()
                }
                MichiButton {
                    text: "Eliminar perfil"
                    variant: "danger"
                    enabled: root._editing
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._deleteProfile()
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        root._editing = false
                        root._validationError = ""
                        if (root.nav) root.nav.back()
                    }
                }
            }
        }
    }
}
