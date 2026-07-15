import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

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

    property var formatModel: ["FLAC", "MP3", "OGG", "Opus", "WAV", "AAC"]
    property var codecMap: {"FLAC":"flac","MP3":"libmp3lame","OGG":"libvorbis","Opus":"libopus","WAV":"pcm_s16le","AAC":"aac"}
    property var sampleRateModel: ["8000","11025","16000","22050","44100","48000","96000","192000","Original"]
    property var bitDepthModel: ["8","16","24","32","Original"]
    property var channelsModel: ["1","2","6","8","Original"]

    objectName: "audioProfiles.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Perfiles de conversión"

    function saveProfile() {
        if (!root.profileName.trim()) return
        if (root.nav) root.nav.navigate("audio_lab_conversion")
    }

    function deleteProfile() {
        if (root.nav) root.nav.navigate("audio_lab_conversion")
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "audioProfiles.focusScope"
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
                    text: root.isEditing ? "Editar perfil" : "Nuevo perfil de conversión"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: root.isEditing ? "Editar perfil" : "Nuevo perfil"
                }

                SectionHeader { text: "Nombre del perfil"; width: parent.width; objectName: "profiles.section.name" }

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
                    objectName: "profiles.nameArea"
                    height: 60
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                        anchors.verticalCenter: parent.verticalCenter
                        TextField {
                            id: nameField
                            objectName: "profiles.nameField"
                            width: parent.width
                            placeholderText: "Nombre del perfil"
                            text: root.profileName
                            font.pixelSize: MichiTheme.typography.bodySize
                            color: MichiTheme.colors.textPrimary
                            background: Rectangle {
                                color: MichiTheme.colors.surfaceInput
                                radius: MichiTheme.radiusSm
                                border.width: parent.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                                border.color: parent.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                            }
                            Accessible.name: "Nombre del perfil"
                            onTextChanged: root.profileName = text
                        }
                    }
                }

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
                    }
                }
            }
        }
    }
}
