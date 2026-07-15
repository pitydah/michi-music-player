import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property string state: "READY"

    objectName: "settings.audio"
    Accessible.role: Accessible.Panel
    Accessible.name: "Audio"
    Accessible.description: "Configuración avanzada de audio, frecuencias y búfer"

    signal closeRequested()
    signal openDiagnostics()

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
            objectName: "settings.audio.loading"
            title: "Cargando audio"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.audio.error"
            title: "Audio no disponible"
            message: "No se pudo conectar con el servicio de audio."
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
            objectName: "settings.audio.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Audio"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección Audio"
                }

                Text {
                    text: "Configuración avanzada de audio y motor de reproducción"
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
                        text: "Dispositivo"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Dispositivo de salida"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: outputDeviceCombo
                            objectName: "settings.audio.outputDevice"
                            model: ["Predeterminado", "ALSA: hw:0", "PulseAudio", "PipeWire"]
                            currentIndex: 0
                            Accessible.name: "Dispositivo de salida de audio"
                            KeyNavigation.tab: sampleRateCombo
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Calidad"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Frecuencia de muestreo"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: sampleRateCombo
                            objectName: "settings.audio.sampleRate"
                            model: ["44100 Hz", "48000 Hz", "88200 Hz", "96000 Hz", "192000 Hz"]
                            currentIndex: 1
                            Accessible.name: "Frecuencia de muestreo"
                            KeyNavigation.tab: bitDepthCombo
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Profundidad de bits"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: bitDepthCombo
                            objectName: "settings.audio.bitDepth"
                            model: ["16 bits", "24 bits", "32 bits float"]
                            currentIndex: 1
                            Accessible.name: "Profundidad de bits"
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
                            objectName: "settings.audio.bufferSize"
                            from: 50; to: 5000; value: 200
                            stepSize: 50
                            editable: true
                            Accessible.name: "Tamaño de búfer"
                            KeyNavigation.tab: expertModeSwitch
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Modo experto"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Activar modo experto"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: expertModeSwitch
                            objectName: "settings.audio.expertMode"
                            checked: false
                            Accessible.name: "Activar modo experto de audio"
                            Accessible.description: "Muestra opciones avanzadas de configuración de audio"
                            KeyNavigation.tab: diagnosticsBtn
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm
                        visible: expertModeSwitch.checked

                        Text {
                            text: "Opciones avanzadas visibles en modo experto."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Diagnóstico"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Ejecutar diagnóstico de audio"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        MichiButton {
                            id: diagnosticsBtn
                            objectName: "settings.audio.diagnostics"
                            text: "Abrir diagnóstico"
                            variant: "primary"
                            Accessible.name: "Abrir diagnóstico de audio"
                            Accessible.description: "Ejecuta pruebas de diagnóstico del motor de audio"
                            KeyNavigation.tab: outputDeviceCombo
                            onClicked: root.openDiagnostics()
                        }
                    }
                }
            }
        }
    }
}
