import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var nav: typeof navigationBridge !== "undefined" ? navigationBridge : null
    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property string profileName: ""
    property string profileFormat: "FLAC"
    property string profileCodec: "flac"
    property string profileSampleRate: "44100"
    property string profileBitDepth: "16"
    property string profileChannels: "2"
    property bool isEditing: false
    property var editingProfile: null

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property bool _editing: false
    property string _profileName: ""
    property string _profileFormat: "FLAC"
    property string _profileCodec: "flac"
    property int _profileBitrate: 320
    property int _profileSampleRate: 44100
    property int _profileBitDepth: 16
    property int _profileChannels: 2
    property string _validationError: ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var formatModel: ["FLAC", "MP3", "OGG", "Opus", "WAV", "AAC"]
    property var codecMap: {"FLAC":"flac","MP3":"libmp3lame","OGG":"libvorbis","Opus":"libopus","WAV":"pcm_s16le","AAC":"aac"}
    property var sampleRateModel: ["8000","11025","16000","22050","44100","48000","96000","192000","Original"]
    property var bitDepthModel: ["8","16","24","32","Original"]
    property var channelsModel: ["1","2","6","8","Original"]
>>>>>>> Stashed changes

    objectName: "AudioConversionProfileEditor"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de perfiles de conversión"

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
<<<<<<< Updated upstream
=======
        objectName: "audioProfiles.focusScope"
=======
    property bool _editing: false
    property string _profileName: ""
    property string _profileFormat: "FLAC"
    property string _profileCodec: "flac"
    property int _profileBitrate: 320
    property int _profileSampleRate: 44100
    property int _profileBitDepth: 16
    property int _profileChannels: 2
    property string _validationError: ""

    objectName: "AudioConversionProfileEditor"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Editor de perfiles de conversión"

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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root.nav) root.nav.back()
        }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Text {
                text: root._editing ? "Editar perfil: " + root._profileName : "Perfiles de conversión"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "profileEditorTitle"
            }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
>>>>>>> Stashed changes

            Text {
                text: "Portable MP3, Portable AAC, Efficient Opus, Lossless FLAC, Archival FLAC, PCM WAV"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "profileEditorSubtitle"
            }

            SectionHeader { text: "Perfiles predefinidos"; width: parent.width; objectName: "presetsHeader"; Accessible.name: "Perfiles predefinidos" }

            Repeater {
                model: root._presetProfiles

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radiusSm; variant: "base"
                    objectName: "presetProfile_" + index
                    Accessible.name: modelData.name
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
                objectName: "profileValidationError"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "profileEditorPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Nombre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField {
                            width: parent.width - 100; text: root._profileName
                            placeholderText: "Nombre del perfil"
                            objectName: "profileNameField"
                            Accessible.name: "Nombre del perfil"
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radiusSm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._profileName = text
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Formato:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            id: editFormatCombo
                            model: root._formatOptions
                            textRole: "label"
                            width: parent.width - 100
                            objectName: "editFormatCombo"
                            Accessible.name: "Formato"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: {
                                var item = root._formatOptions[currentIndex]
                                if (item) { root._profileFormat = item.label; root._profileCodec = item.codec }
                            }
<<<<<<< Updated upstream
=======
                            Accessible.name: "Nombre del perfil"
                            onTextChanged: root.profileName = text
=======
            Text {
                text: root._editing ? "Editar perfil: " + root._profileName : "Perfiles de conversión"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                objectName: "profileEditorTitle"
            }

            Text {
                text: "Portable MP3, Portable AAC, Efficient Opus, Lossless FLAC, Archival FLAC, PCM WAV"
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; wrapMode: Text.WordWrap; width: parent.width
                objectName: "profileEditorSubtitle"
            }

            SectionHeader { text: "Perfiles predefinidos"; width: parent.width; objectName: "presetsHeader"; Accessible.name: "Perfiles predefinidos" }

            Repeater {
                model: root._presetProfiles

                GlassMaterial {
                    width: parent.width; height: 56; radius: MichiTheme.radiusSm; variant: "base"
                    objectName: "presetProfile_" + index
                    Accessible.name: modelData.name
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
                objectName: "profileValidationError"
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                objectName: "profileEditorPanel"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Nombre:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        TextField {
                            width: parent.width - 100; text: root._profileName
                            placeholderText: "Nombre del perfil"
                            objectName: "profileNameField"
                            Accessible.name: "Nombre del perfil"
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle { color: MichiTheme.colors.surfaceInput; radius: MichiTheme.radiusSm; border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth; border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard }
                            onTextChanged: root._profileName = text
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Formato:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            id: editFormatCombo
                            model: root._formatOptions
                            textRole: "label"
                            width: parent.width - 100
                            objectName: "editFormatCombo"
                            Accessible.name: "Formato"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: {
                                var item = root._formatOptions[currentIndex]
                                if (item) { root._profileFormat = item.label; root._profileCodec = item.codec }
                            }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bitrate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            model: root._bitrateOptions
                            width: parent.width - 100
                            objectName: "editBitrateCombo"
                            Accessible.name: "Bitrate"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileBitrate = root._bitrateOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Sample rate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            model: root._sampleRateOptions
                            width: parent.width - 100
                            objectName: "editSampleRateCombo"
                            Accessible.name: "Sample rate"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileSampleRate = root._sampleRateOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Bit depth:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            model: root._bitDepthOptions
                            width: parent.width - 100
                            objectName: "editBitDepthCombo"
                            Accessible.name: "Bit depth"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileBitDepth = root._bitDepthOptions[currentIndex]
                        }
                    }

                    Row {
                        spacing: MichiTheme.spacing.md; width: parent.width
                        Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; width: 100 }
                        ComboBox {
                            model: root._channelsOptions
                            width: parent.width - 100
                            objectName: "editChannelsCombo"
                            Accessible.name: "Canales"
                            activeFocusOnTab: true
                            onCurrentIndexChanged: root._profileChannels = root._channelsOptions[currentIndex]
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Guardar perfil"
                    variant: "primary"
                    enabled: root._profileName.trim() !== ""
                    objectName: "saveProfileBtn"
                    Accessible.name: "Guardar perfil"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._saveProfile()
                }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                SectionHeader { text: "Configuración"; width: parent.width; objectName: "profiles.section.config" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "accent"
                    objectName: "profiles.config"
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Formato:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: formatCombo
                                objectName: "profiles.formatCombo"
                                model: root.formatModel
                                currentIndex: 0
                                Accessible.name: "Formato de salida"
                                onCurrentTextChanged: {
                                    root.profileFormat = currentText
                                    root.profileCodec = root.codecMap[currentText] || "flac"
                                }
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Codec:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: root.profileCodec; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Sample rate:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: sampleRateCombo
                                objectName: "profiles.sampleRateCombo"
                                model: root.sampleRateModel
                                currentIndex: 4
                                Accessible.name: "Sample rate"
                                onCurrentTextChanged: root.profileSampleRate = currentText
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Bit depth:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: bitDepthCombo
                                objectName: "profiles.bitDepthCombo"
                                model: root.bitDepthModel
                                currentIndex: 1
                                Accessible.name: "Bit depth"
                                onCurrentTextChanged: root.profileBitDepth = currentText
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.sm
                            Text { text: "Canales:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                            ComboBox {
                                id: channelsCombo
                                objectName: "profiles.channelsCombo"
                                model: root.channelsModel
                                currentIndex: 1
                                Accessible.name: "Canales"
                                onCurrentTextChanged: root.profileChannels = currentText
                            }
                        }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: "Guardar perfil"
                        variant: "primary"
                        objectName: "profiles.saveBtn"
                        enabled: root.profileName.trim() !== ""
                        onClicked: root.saveProfile()
                        Accessible.name: "Guardar perfil"
                    }
                    MichiButton {
                        text: "Eliminar perfil"
                        variant: "danger"
                        objectName: "profiles.deleteBtn"
                        visible: root.isEditing
                        onClicked: root.deleteProfile()
                        Accessible.name: "Eliminar perfil"
                    }
                    MichiButton {
                        text: "Cancelar"; variant: "ghost"
                        objectName: "profiles.cancelBtn"
                        onClicked: { if (root.nav) root.nav.back() }
                        Accessible.name: "Cancelar"
=======
            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Guardar perfil"
                    variant: "primary"
                    enabled: root._profileName.trim() !== ""
                    objectName: "saveProfileBtn"
                    Accessible.name: "Guardar perfil"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._saveProfile()
                }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                MichiButton {
                    text: "Eliminar perfil"
                    variant: "danger"
                    enabled: root._editing
                    objectName: "deleteProfileBtn"
                    Accessible.name: "Eliminar perfil"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: root._deleteProfile()
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    objectName: "cancelProfileBtn"
                    Accessible.name: "Cancelar"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        root._editing = false
                        root._validationError = ""
                        if (root.nav) root.nav.back()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    }
                }
            }
        }
    }
}
