import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Appearance"
    focus: true
    id: root
    objectName: "settingsAppearancePage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var themeBridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""


    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
        if (root.themeBridge && typeof root.themeBridge.applySetting === "function")
            root.themeBridge.applySetting(key, value)
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                
                

                PageHeader {
                    title: "Apariencia"
                    subtitle: "Tema, colores y disposición visual"
                }

                GlassCard {
                    id: colorsCard
                    Layout.fillWidth: true
                    title: "Colores"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Color de acento"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Color principal para elementos interactivos"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            RowLayout {
                                spacing: MichiTheme.spacing.sm

                                Repeater {
                                    model: [
                                        { color: "#8FB7FF", name: "Azul" },
                                        { color: "#A78BFA", name: "Morado" },
                                        { color: "#FF7A00", name: "Naranja" },
                                        { color: "#4ADE80", name: "Verde" },
                                        { color: "#F87171", name: "Rojo" },
                                        { color: "#F0F2F8", name: "Blanco" }
                                    ]

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: width / 2
                                        color: modelData.color
                                        border.width: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? 3 : 1
                                        border.color: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? MichiTheme.colors.textPrimary : MichiTheme.colors.borderCard


                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root._saveValue("appearance/accent_color", modelData.color)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Apariencia"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Modo oscuro"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Alternar entre tema oscuro y claro"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            Switch {
                                id: darkModeSwitch
                                checked: root._loadValue("appearance/dark_mode", true)
                                onClicked: {
                                    root._saveValue("appearance/dark_mode", checked)
                                    MichiTheme.setDarkMode(checked)
                                }
                                Accessible.description: "Alternar modo oscuro/claro"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }
                    }
                }

                GlassCard {
                    id: typographyCard
                    Layout.fillWidth: true
                    title: "Tipografía"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Escala de fuente"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: fontScaleSlider.value + "%"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                Accessible.role: Accessible.Slider

                                id: fontScaleSlider
                                activeFocusOnTab: true

                                implicitWidth: 200
                                from: 75
                                to: 150
                                value: root._loadValue("appearance/font_scale", 100)
                                stepSize: 5
                                accessibleName: "Escala de fuente"
                                onMoved: root._saveValue("appearance/font_scale", value)
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("appearance/font_scale", value)
                                }
                                Accessible.description: "Ajusta el tamaño de la fuente: " + value + "%"
                            }
                        }
                    }
                }

                GlassCard {
                    id: visualCard
                    Layout.fillWidth: true
                    title: "Preferencias visuales"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Movimiento reducido"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: reducedMotion
                                checked: root._loadValue("appearance/reduced_motion", false)
                                onClicked: root._saveValue("appearance/reduced_motion", checked)
                                Accessible.description: "Reducir animaciones y transiciones"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Transparencia reducida"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: reducedTransparency
                                checked: root._loadValue("appearance/reduced_transparency", false)
                                onClicked: root._saveValue("appearance/reduced_transparency", checked)
                                Accessible.description: "Reducir efectos de transparencia y desenfoque"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Modo compacto"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: compactMode
                                checked: root._loadValue("interface/compact_mode", false)
                                onClicked: root._saveValue("interface/compact_mode", checked)
                                Accessible.description: "Reducir espacios y márgenes"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Carátula como fondo"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: coverAsBackdrop
                                checked: root._loadValue("appearance/cover_as_backdrop", false)
                                onClicked: root._saveValue("appearance/cover_as_backdrop", checked)
                                Accessible.description: "Usar la carátula del álbum actual como fondo"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: menuCard
                    Layout.fillWidth: true
                    title: "Barra de menú"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mostrar barra de menú"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: showMenubar
                                checked: root._loadValue("interface/show_menubar", true)
                                onClicked: root._saveValue("interface/show_menubar", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
}
