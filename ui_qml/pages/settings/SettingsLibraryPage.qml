import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt.labs.platform
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings Library"
    focus: true
    id: root
    objectName: "settingsLibraryPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var musicFolders: []


    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadFolders()
    }

    function _loadFolders() {
        if (!root.bridge) return
        var folders = root.bridge.getValue("library/music_folders")
        root.musicFolders = folders || []
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

    function _addFolder(path) {
        if (!root.bridge || !path) return
        var result = root.bridge.setValue("library/add_folder", path)
        if (result && result.ok) {
            if (root.notif) root.notif.showMessage("Carpeta agregada", "info")
            _loadFolders()
        } else {
            if (root.notif) root.notif.showMessage("Error al agregar carpeta", "error")
        }
    }

    function _removeFolder(path) {
        if (!root.bridge || !path) return
        var result = root.bridge.setValue("library/remove_folder", path)
        if (result && result.ok) {
            if (root.notif) root.notif.showMessage("Carpeta eliminada", "info")
            _loadFolders()
        } else {
            if (root.notif) root.notif.showMessage("Error al eliminar carpeta", "error")
        }
    }

    function _rescanLibrary() {
        if (!root.bridge) return
        root.bridge.setValue("library/rescan", true)
        if (root.notif) root.notif.showMessage("Reescaneo iniciado", "info")
    }

    function _clearAndRescan() {
        if (!root.bridge) return
        root.bridge.setValue("library/clear_and_rescan", true)
        if (root.notif) root.notif.showMessage("Biblioteca limpiada y reescaneo iniciado", "info")
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            anchors.fill: parent
            clip: true

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg

                PageHeader {
                    title: "Biblioteca"
                    subtitle: "Carpetas, escaneo y mantenimiento"
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Carpetas de música"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        ListView {
                            Accessible.role: Accessible.List

                            Accessible.name: "ListView"

                            activeFocusOnTab: true

                            focusPolicy: Qt.StrongFocus
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(contentHeight, 300)
                            model: root.musicFolders
                            clip: true
                            spacing: MichiTheme.spacing.sm
                            interactive: true

                            delegate: Rectangle {
                                width: foldersList.width
                                height: 48
                                radius: MichiTheme.radius.sm
                                color: MichiTheme.colors.surfaceCard

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: MichiTheme.spacing.sm
                                    spacing: MichiTheme.spacing.sm

                                    Label {
                                        text: modelData
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                        Accessible.role: Accessible.Button

                                        activeFocusOnTab: true

                                    }

                                    MichiButton {
                                        text: "Eliminar"
                                        variant: "danger"
                                        implicitWidth: 80
                                        onClicked: root._removeFolder(modelData)
                                    }
                                }

                            }

                            Item {
                                anchors.centerIn: parent
                                visible: foldersList.count === 0
                                Label {
                                    text: "No hay carpetas configuradas"
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.bodySize
                            Accessible.role: Accessible.Button

                            activeFocusOnTab: true

                                }
                            }
                        }

                        MichiButton {
                            text: "Añadir carpeta de música"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: folderDialog.open()
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Escaneo"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Vigilar cambios en carpetas"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("library/watch_changes", true)
                                onClicked: root._saveValue("library/watch_changes", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Escanear al iniciar"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("library/auto_scan", true)
                                onClicked: root._saveValue("library/auto_scan", checked)
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: MichiTheme.spacing.xxs
                                Label {
                                    text: "Modo de indexación"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Rápido solo analiza cambios, completo reindexa todo"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ListModel {
                                    ListElement { text: "Rápido"; value: "quick" }
                                    ListElement { text: "Completo"; value: "full" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var m = root._loadValue("library/indexer_mode", "quick")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === m) return i
                                    return 0
                                }
                                onActivated: root._saveValue("library/indexer_mode", currentValue)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Carátulas"
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
                                    text: "Extracción de carátulas"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Prioridad para obtener carátulas"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                focusPolicy: Qt.StrongFocus
                                model: ListModel {
                                    ListElement { text: "Incrustada"; value: "embedded" }
                                    ListElement { text: "Archivo externo"; value: "external" }
                                    ListElement { text: "Preferir incrustada"; value: "prefer_embedded" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var m = root._loadValue("library/cover_art_mode", "prefer_embedded")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === m) return i
                                    return 2
                                }
                                onActivated: root._saveValue("library/cover_art_mode", currentValue)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Enriquecimiento de metadatos"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Enriquecimiento automático"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: root._loadValue("artist_enrichment/enabled", false)
                                onClicked: root._saveValue("artist_enrichment/enabled", checked)
                                Accessible.description: "Obtener metadatos de MusicBrainz y otras fuentes"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Mantenimiento"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            text: "Reescanear biblioteca"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._rescanLibrary()
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Limpiar y reescanear biblioteca"
                            variant: "danger"
                            Layout.fillWidth: true
                            onClicked: confirmRescan.open()
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    FolderDialog {
        title: "Seleccionar carpeta de música"
        onAccepted: {
            var folderPath = folder.toString().replace("file://", "")
            if (folderPath) root._addFolder(folderPath)
        }
    }

    ConfirmActionDialog {
        title: "Limpiar y reescanear biblioteca"
        message: "¿Estás seguro? Esta acción eliminará la base de datos actual y reescaneará todas las carpetas desde cero. Esta operación no puede deshacerse."
        danger: true
        onConfirmed: root._clearAndRescan()
    }

    Keys.onEscapePressed: {
        if (confirmRescan.open) confirmRescan.open = false
        else root.closeRequested()
    }

    signal closeRequested()
}
