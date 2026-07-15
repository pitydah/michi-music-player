import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property string state: "READY"

    objectName: "settings.accessibility"
    Accessible.role: Accessible.Panel
    Accessible.name: "Accesibilidad"
    Accessible.description: "Opciones de accesibilidad auditiva y visual"

    signal closeRequested()

    states: [
        State { name: "LOADING"; PropertyChanges { target: loader; sourceComponent: loadingComp } },
        State { name: "READY"; PropertyChanges { target: loader; sourceComponent: readyComp } },
        State { name: "ERROR"; PropertyChanges { target: loader; sourceComponent: errorComp } }
    ]
    state: "READY"

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
            objectName: "settings.accessibility.loading"
            title: "Cargando accesibilidad"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.accessibility.error"
            title: "Accesibilidad no disponible"
            message: "No se pudo cargar la configuración."
            retryText: "Reintentar"
            onRetryRequested: root.state = "READY"
        }
    }

    Component {
        id: readyComp
        Flickable {
            anchors.fill: parent
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            objectName: "settings.accessibility.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Accesibilidad"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección Accesibilidad"
                }

                Text {
                    text: "Opciones para mejorar la accesibilidad visual y auditiva"
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
                        text: "Audio"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Mono"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: monoSswitch
                            objectName: "settings.accessibility.mono"
                            checked: false
                            Accessible.name: "Audio mono"
                            Accessible.description: "Combinar canales izquierdo y derecho en mono"
                            KeyNavigation.tab: balanceSlider
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Balance"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        MichiSlider {
                            id: balanceSlider
                            objectName: "settings.accessibility.balance"
                            Layout.preferredWidth: 160
                            from: -100; to: 100; value: 0
                            stepSize: 1
                            accessibleName: "Balance de audio"
                            KeyNavigation.tab: fontScaleCombo
                        }

                        Text {
                            text: balanceSlider.value > 0 ? "D+" + balanceSlider.value
                                 : balanceSlider.value < 0 ? "I" + (-balanceSlider.value)
                                 : "Centro"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            implicitWidth: 48
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Visual"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Escala de fuente"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: fontScaleCombo
                            objectName: "settings.accessibility.fontScale"
                            model: ["Pequeña", "Normal", "Grande", "Muy grande"]
                            currentIndex: root.bridge && root.bridge.fontScale === "large" ? 2 : 1
                            Accessible.name: "Escala de fuente"
                            KeyNavigation.tab: highContrastSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Alto contraste"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: highContrastSwitch
                            objectName: "settings.accessibility.highContrast"
                            checked: root.bridge ? root.bridge.highContrast : false
                            Accessible.name: "Alto contraste"
                            Accessible.description: "Aumentar el contraste de la interfaz"
                            KeyNavigation.tab: reduceMotionSwitchAcc
                            onClicked: {
                                if (root.bridge) root.bridge.highContrast = checked
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Reducir movimiento"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: reduceMotionSwitchAcc
                            objectName: "settings.accessibility.reduceMotion"
                            checked: root.bridge ? root.bridge.reduceMotion : false
                            Accessible.name: "Reducir movimiento"
                            Accessible.description: "Reducir animaciones y transiciones"
                            KeyNavigation.tab: announceTrackToggle
                            onClicked: {
                                if (root.bridge) root.bridge.reduceMotion = checked
                            }
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Anuncios"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Anunciar cambios de pista"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: announceTrackToggle
                            objectName: "settings.accessibility.announceTrack"
                            checked: false
                            Accessible.name: "Anunciar cambios de pista"
                            KeyNavigation.tab: announcePlaybackToggle
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Anunciar estado de reproducción"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: announcePlaybackToggle
                            objectName: "settings.accessibility.announcePlayback"
                            checked: false
                            Accessible.name: "Anunciar estado de reproducción"
                            KeyNavigation.tab: monoSswitch
                        }
                    }
                }
            }
        }
    }
}
