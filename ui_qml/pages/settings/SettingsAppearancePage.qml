import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property string state: "READY"

    objectName: "settings.appearance"
    Accessible.role: Accessible.Panel
    Accessible.name: "Apariencia"
    Accessible.description: "Color de acento, tipografía y efectos visuales"

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
            objectName: "settings.appearance.loading"
            title: "Cargando apariencia"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.appearance.error"
            title: "Apariencia no disponible"
            message: "No se pudo conectar con ThemeBridge."
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
            objectName: "settings.appearance.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Apariencia"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección Apariencia"
                }

                Text {
                    text: "Personaliza el aspecto visual de Michi"
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
                        text: "Color de acento"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Flow {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        Repeater {
                            model: ["#8FB7FF", "#FF7A00", "#4ADE80", "#F87171", "#A78BFA", "#FBBF24"]
                            Rectangle {
                                id: swatch
                                width: 36; height: 36; radius: MichiTheme.radiusPill
                                color: modelData
                                border.width: root.bridge && root.bridge.accentColor === modelData ? 2 : 1
                                border.color: root.bridge && root.bridge.accentColor === modelData ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderCard
                                objectName: "settings.appearance.accentColor." + modelData.replace("#", "")
                                Accessible.name: "Color " + modelData
                                Accessible.role: Accessible.Button

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.bridge) root.bridge.accentColor = modelData
                                    }
                                }

                                Keys.onReturnPressed: {
                                    if (root.bridge) root.bridge.accentColor = modelData
                                }
                                Keys.onSpacePressed: {
                                    if (root.bridge) root.bridge.accentColor = modelData
                                }
                                focus: true
                                activeFocusOnTab: true
                            }
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Tipografía"
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
                            objectName: "settings.appearance.fontScale"
                            model: ["Pequeña", "Normal", "Grande", "Muy grande"]
                            currentIndex: 1
                            Accessible.name: "Escala de fuente"
                            KeyNavigation.tab: reduceMotionSwitch
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Efectos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
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
                            id: reduceMotionSwitch
                            objectName: "settings.appearance.reduceMotion"
                            checked: root.bridge ? root.bridge.reduceMotion : false
                            Accessible.name: "Reducir movimiento"
                            Accessible.description: "Reducir animaciones y transiciones"
                            KeyNavigation.tab: reduceTransparencySwitch
                            onClicked: {
                                if (root.bridge) root.bridge.reduceMotion = checked
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Reducir transparencia"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: reduceTransparencySwitch
                            objectName: "settings.appearance.reduceTransparency"
                            checked: false
                            Accessible.name: "Reducir transparencia"
                            Accessible.description: "Reducir efectos de transparencia y vidrio"
                            KeyNavigation.tab: compactModeSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Modo compacto"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: compactModeSwitch
                            objectName: "settings.appearance.compactMode"
                            checked: root.bridge ? root.bridge.compactMode : false
                            Accessible.name: "Modo compacto"
                            Accessible.description: "Interfaz más densa con menos espaciado"
                            KeyNavigation.tab: coverBackdropSwitch
                            onClicked: {
                                if (root.bridge) root.bridge.compactMode = checked
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Fondo de carátula"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: coverBackdropSwitch
                            objectName: "settings.appearance.coverBackdrop"
                            checked: true
                            Accessible.name: "Fondo de carátula"
                            Accessible.description: "Usar la carátula como fondo decorativo"
                            KeyNavigation.tab: fontScaleCombo
                        }
                    }
                }
            }
        }
    }
}
