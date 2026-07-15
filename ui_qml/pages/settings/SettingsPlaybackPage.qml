import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property string state: "READY"

    objectName: "settings.playback"
    Accessible.role: Accessible.Panel
    Accessible.name: "Reproducción"
    Accessible.description: "Salida de audio, volumen, crossfade y ReplayGain"

    signal closeRequested()

    states: [
        State { name: "LOADING"; PropertyChanges { target: loader; sourceComponent: loadingComp } },
        State { name: "READY"; PropertyChanges { target: loader; sourceComponent: readyComp } },
        State { name: "ERROR"; PropertyChanges { target: loader; sourceComponent: errorComp } }
    ]
    state: root.bridge ? "READY" : "ERROR"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true

        Keys.onEscapePressed: root.closeRequested()

        Loader {
            id: loader
            anchors.fill: parent
        }
    }

    Component {
        id: loadingComp
        LoadingState {
            objectName: "settings.playback.loading"
            title: "Cargando ajustes de reproducción"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.playback.error"
            title: "Ajustes no disponibles"
            message: "No se pudo conectar con el servicio de configuración."
            retryText: "Reintentar"
            onRetryRequested: root.state = root.bridge ? "READY" : "ERROR"
        }
    }

    Component {
        id: readyComp
        Flickable {
            anchors.fill: parent
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            objectName: "settings.playback.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Reproducción"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección Reproducción"
                }

                Text {
                    text: "Configuración de salida y comportamiento de reproducción"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Dispositivo de salida"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Dispositivo de audio"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: outputDeviceCombo
                            objectName: "settings.playback.outputDevice"
                            model: ["Predeterminado", "HDMI", "USB DAC", "Bluetooth"]
                            currentIndex: 0
                            Accessible.name: "Dispositivo de salida de audio"
                            KeyNavigation.tab: audioProfileCombo
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Perfil de audio"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Perfil"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: audioProfileCombo
                            objectName: "settings.playback.audioProfile"
                            model: ["Estándar", "Hi-Fi", "Bit-perfect", "MPD"]
                            currentIndex: 0
                            Accessible.name: "Perfil de audio"
                            KeyNavigation.tab: volumeSlider
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Volumen"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Volumen por defecto"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        MichiSlider {
                            id: volumeSlider
                            objectName: "settings.playback.volume"
                            Layout.preferredWidth: 200
                            from: 0; to: 100; value: 75
                            stepSize: 1
                            accessibleName: "Volumen por defecto"
                            KeyNavigation.tab: gaplessSwitch
                        }

                        Text {
                            text: Math.round(volumeSlider.value) + "%"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            implicitWidth: 40
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Comportamiento"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Reproducción sin pausas (gapless)"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: gaplessSwitch
                            objectName: "settings.playback.gapless"
                            checked: true
                            Accessible.name: "Reproducción sin pausas"
                            KeyNavigation.tab: crossfadeSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Crossfade"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: crossfadeSwitch
                            objectName: "settings.playback.crossfade"
                            checked: false
                            Accessible.name: "Crossfade entre canciones"
                            KeyNavigation.tab: crossfadeDurationSlider
                        }

                        MichiSlider {
                            id: crossfadeDurationSlider
                            objectName: "settings.playback.crossfadeDuration"
                            Layout.preferredWidth: 120
                            from: 0; to: 12; value: 3
                            stepSize: 1
                            enabled: crossfadeSwitch.checked
                            accessibleName: "Duración de crossfade"
                            KeyNavigation.tab: replaygainCombo
                        }

                        Text {
                            text: crossfadeDurationSlider.value + " s"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            implicitWidth: 36
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "ReplayGain"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Modo ReplayGain"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: replaygainCombo
                            objectName: "settings.playback.replaygainMode"
                            model: ["Desactivado", "Pista", "Álbum", "Inteligente"]
                            currentIndex: 0
                            Accessible.name: "Modo ReplayGain"
                            KeyNavigation.tab: bufferSizeSpinBox
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Tamaño de búfer (ms)"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        SpinBox {
                            id: bufferSizeSpinBox
                            objectName: "settings.playback.bufferSize"
                            from: 100; to: 5000; value: 2000
                            stepSize: 100
                            editable: true
                            Accessible.name: "Tamaño de búfer"
                            KeyNavigation.tab: outputDeviceCombo
                        }
                    }
                }
            }
        }
    }
}
