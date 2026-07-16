import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings General"
    focus: true
    id: root
    objectName: "settingsGeneralPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property real cacheSize: 0.0
    property bool loadingCache: false


    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _queryCacheSize()
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
    }

    function _queryCacheSize() {
        root.loadingCache = true
        if (!root.bridge) { root.loadingCache = false; return }
        var size = root.bridge.getValue("cache/total_size_mb")
        root.cacheSize = size !== null ? parseFloat(size) || 0 : 0
        root.loadingCache = false
    }

    function _clearCache() {
        if (!root.bridge) return
        var result = root.bridge.setValue("cache/clear", true)
        if (result && result.ok) {
            if (root.notif) root.notif.showMessage("Caché limpiada", "info")
            root.cacheSize = 0
        } else {
            if (root.notif) root.notif.showMessage("Error al limpiar caché", "error")
        }
    }

    function _checkForUpdates() {
        if (!root.bridge) return
        root.bridge.setValue("updates/check_now", true)
        if (root.notif) root.notif.showMessage("Buscando actualizaciones...", "info")
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
                Layout.topMargin: MichiTheme.spacing.xl
                Layout.bottomMargin: MichiTheme.spacing.xl

                PageHeader {
                    title: "General"
                    subtitle: "Idioma, comportamiento y preferencias de ventana"
                }

                GlassCard {
                    id: languageCard
                    Layout.fillWidth: true
                    title: "Idioma"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Idioma de la interfaz"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Requiere reiniciar la aplicación"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                id: languageSelector
                                model: ListModel {
                                    ListElement { text: "Español"; value: "es" }
                                    ListElement { text: "English"; value: "en" }
                                    ListElement { text: "Français"; value: "fr" }
                                    ListElement { text: "Deutsch"; value: "de" }
                                    ListElement { text: "Português"; value: "pt" }
                                    ListElement { text: "Italiano"; value: "it" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var lang = root._loadValue("general/language", "es")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === lang) return i
                                    return 0
                                }
                                onActivated: root._saveValue("general/language", currentValue)
                                Accessible.description: "Selecciona el idioma de la interfaz"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: themeCard
                    Layout.fillWidth: true
                    title: "Tema"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Modo de tema"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Sistema, claro u oscuro"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                id: themeMode
                                model: ListModel {
                                    ListElement { text: "Sistema"; value: "system" }
                                    ListElement { text: "Claro"; value: "light" }
                                    ListElement { text: "Oscuro"; value: "dark" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var t = root._loadValue("appearance/theme", "dark")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === t) return i
                                    return 0
                                }
                                onActivated: root._saveValue("appearance/theme", currentValue)
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: behaviorCard
                    Layout.fillWidth: true
                    title: "Comportamiento de ventana"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Cerrar a la bandeja"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: closeToTray
                                checked: root._loadValue("general/close_to_tray", false)
                                onClicked: root._saveValue("general/close_to_tray", checked)
                                Accessible.description: "Minimizar a la bandeja del sistema al cerrar"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Iniciar minimizado"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: startMinimized
                                checked: root._loadValue("general/start_minimized", false)
                                onClicked: root._saveValue("general/start_minimized", checked)
                                Accessible.description: "Abrir la aplicación minimizada en la bandeja"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Recordar sesión"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: rememberSession
                                checked: root._loadValue("general/remember_session", true)
                                onClicked: root._saveValue("general/remember_session", checked)
                                Accessible.description: "Restaurar la última vista y cola al abrir"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Confirmar salida"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: confirmExit
                                checked: root._loadValue("general/confirm_exit", false)
                                onClicked: root._saveValue("general/confirm_exit", checked)
                                Accessible.description: "Preguntar antes de cerrar la aplicación"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: updatesCard
                    Layout.fillWidth: true
                    title: "Actualizaciones"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Buscar actualizaciones automáticamente"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: checkUpdates
                                checked: root._loadValue("updates/auto_check", true)
                                onClicked: root._saveValue("updates/auto_check", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Buscar actualizaciones ahora"
                            variant: "ghost"
                            Layout.fillWidth: true
                            onClicked: root._checkForUpdates()
                        }
                    }
                }

                GlassCard {
                    id: cacheCard
                    Layout.fillWidth: true
                    title: "Caché"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Tamaño de caché"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    id: cacheSizeLabel
                                    text: root.loadingCache ? "Calculando..." : (root.cacheSize > 0 ? root.cacheSize.toFixed(1) + " MB" : "0 MB")
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiButton {
                                id: clearCacheBtn
                                text: "Limpiar caché"
                                variant: "danger"
                                enabled: root.cacheSize > 0 && !root.loadingCache
                                onClicked: confirmClearCache.open()
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    ConfirmActionDialog {
        id: confirmClearCache
        title: "Limpiar caché"
        message: "¿Estás seguro de que deseas limpiar la caché? Los datos se volverán a descargar según sea necesario."
        danger: true
        onConfirmed: root._clearCache()
    }

    Keys.onEscapePressed: {
        if (confirmClearCache.open) confirmClearCache.open = false
        else root.closeRequested()
    }

    signal closeRequested()
}
