import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property string state: "READY"

    objectName: "settings.general"
    Accessible.role: Accessible.Panel
    Accessible.name: "Ajustes generales"
    Accessible.description: "Idioma, comportamiento de ventana y gestión de caché"

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
        Keys.onEnterPressed: { if (focusScope.focus) focusScope.focus = false }

        Loader {
            id: loader
            anchors.fill: parent
        }
    }

    Component {
        id: loadingComp
        LoadingState {
            objectName: "settings.general.loading"
            title: "Cargando ajustes generales"
            message: "Obteniendo configuración..."
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.general.error"
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
            objectName: "settings.general.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "General"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección General"
                }

                Text {
                    text: "Idioma, comportamiento de ventana y caché"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: true
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Idioma"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        Accessible.name: "Idioma"
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Idioma de la interfaz"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: langCombo
                            objectName: "settings.general.language"
                            model: ["Español", "English", "Português", "Français", "Deutsch"]
                            currentIndex: 0
                            Accessible.name: "Seleccionar idioma"
                            Accessible.description: "Idioma de la interfaz de usuario"
                            KeyNavigation.tab: themeModeCombo
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Apariencia"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        Accessible.name: "Apariencia"
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Modo de tema"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: themeModeCombo
                            objectName: "settings.general.themeMode"
                            model: ["Oscuro", "Claro", "Sistema"]
                            currentIndex: 0
                            Accessible.name: "Modo de tema"
                            Accessible.description: "Oscuro, claro o seguir el sistema"
                            KeyNavigation.tab: closeToTraySwitch
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Ventana"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        Accessible.name: "Ventana"
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Cerrar a la bandeja"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: closeToTraySwitch
                            objectName: "settings.general.closeToTray"
                            checked: false
                            Accessible.name: "Cerrar a la bandeja"
                            Accessible.description: "Al cerrar la ventana, minimizar a la bandeja del sistema"
                            KeyNavigation.tab: startMinimizedSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Iniciar minimizado"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: startMinimizedSwitch
                            objectName: "settings.general.startMinimized"
                            checked: false
                            Accessible.name: "Iniciar minimizado"
                            Accessible.description: "Iniciar la aplicación minimizada en la bandeja"
                            KeyNavigation.tab: cacheBtn
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Caché"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                        Accessible.name: "Caché"
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Tamaño de caché: 256 MB"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        MichiButton {
                            id: cacheBtn
                            objectName: "settings.general.clearCache"
                            text: "Limpiar caché"
                            variant: "danger"
                            Accessible.name: "Limpiar caché"
                            Accessible.description: "Eliminar todos los archivos de caché"
                            KeyNavigation.tab: resetBtn
                            onClicked: confirmCacheDialog.open()
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                RowLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Item { Layout.fillWidth: true }

                    MichiButton {
                        id: resetBtn
                        objectName: "settings.general.resetCategory"
                        text: "Restaurar valores"
                        variant: "ghost"
                        Accessible.name: "Restaurar valores generales"
                        KeyNavigation.tab: cacheBtn
                        onClicked: confirmResetDialog.open()
                    }
                }
            }
        }
    }

    ConfirmActionDialog {
        id: confirmResetDialog
        objectName: "settings.general.resetConfirm"
        title: "Restaurar ajustes generales"
        message: "¿Estás seguro de que deseas restaurar todos los ajustes generales a sus valores por defecto?"
        confirmText: "Restaurar"
        danger: true
        onConfirmed: {
            if (root.bridge) root.bridge.resetAll()
        }
    }

    ConfirmActionDialog {
        id: confirmCacheDialog
        objectName: "settings.general.clearCacheConfirm"
        title: "Limpiar caché"
        message: "¿Estás seguro de que deseas eliminar todos los archivos de caché?"
        confirmText: "Limpiar"
        danger: true
        onConfirmed: {
            console.log("[Settings] Caché limpiada")
        }
    }
}
