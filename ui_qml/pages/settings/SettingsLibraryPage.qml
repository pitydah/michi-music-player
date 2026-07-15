import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import Qt.labs.platform
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
import Qt.labs.platform
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import "../../theme"
import "../../components"

Item {
    id: root
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    objectName: "settingsLibraryPage"
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var musicFolders: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de biblioteca"

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
            objectName: "settings.library.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de biblioteca"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Biblioteca"
                    subtitle: "Carpetas, escaneo y mantenimiento"
                }

                GlassCard {
                    id: foldersCard
                    Layout.fillWidth: true
                    title: "Carpetas de música"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        ListView {
                            id: foldersList
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(contentHeight, 300)
                            model: root.musicFolders
                            clip: true
                            spacing: MichiTheme.spacing.sm
                            interactive: true
                            objectName: "settings.library.foldersList"
                            Accessible.role: Accessible.List
                            Accessible.name: "Carpetas de música"

                            delegate: Rectangle {
                                width: foldersList.width
                                height: 48
                                radius: MichiTheme.radiusSm
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                color: MichiTheme.colors.surfaceCard
=======
=======
>>>>>>> Stashed changes
=======
    objectName: "settingsLibraryPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var musicFolders: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de biblioteca"

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
            objectName: "settings.library.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de biblioteca"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Biblioteca"
                    subtitle: "Carpetas, escaneo y mantenimiento"
                }

                GlassCard {
                    id: foldersCard
                    Layout.fillWidth: true
                    title: "Carpetas de música"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        ListView {
                            id: foldersList
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(contentHeight, 300)
                            model: root.musicFolders
                            clip: true
                            spacing: MichiTheme.spacing.sm
                            interactive: true
                            objectName: "settings.library.foldersList"
                            Accessible.role: Accessible.List
                            Accessible.name: "Carpetas de música"

                            delegate: Rectangle {
                                width: foldersList.width
                                height: 48
                                radius: MichiTheme.radiusSm
                                color: MichiTheme.colors.surfaceCard
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: MichiTheme.spacing.sm
                                    spacing: MichiTheme.spacing.sm

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    Label {
                                        text: modelData
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    Text {
                                        text: modelData.path || ""
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.captionSize
=======
                                    Label {
                                        text: modelData
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                    MichiButton {
                                        text: "Eliminar"
                                        variant: "danger"
                                        implicitWidth: 80
                                        onClicked: root._removeFolder(modelData)
                                        Accessible.name: "Eliminar carpeta " + modelData
                                    }
                                }

                                Accessible.role: Accessible.ListItem
                                Accessible.name: modelData
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                    Text {
                                        text: modelData.available ? "" : "(no disponible)"
                                        color: MichiTheme.colors.error
                                        font.pixelSize: MichiTheme.typography.captionSize
                                        visible: !modelData.available
                                    }
                                }
=======
                                    MichiButton {
                                        text: "Eliminar"
                                        variant: "danger"
                                        implicitWidth: 80
                                        onClicked: root._removeFolder(modelData)
                                        Accessible.name: "Eliminar carpeta " + modelData
                                    }
                                }

                                Accessible.role: Accessible.ListItem
                                Accessible.name: modelData
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            }

                            Item {
                                anchors.centerIn: parent
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                                visible: foldersList.count === 0
                                Label {
                                    text: "No hay carpetas configuradas"
                                    color: MichiTheme.colors.textSecondary
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                                visible: sourcesList.count === 0
                                Text {
                                    text: "No hay carpetas configuradas"
                                    color: MichiTheme.colors.textMuted
=======
                                visible: foldersList.count === 0
                                Label {
                                    text: "No hay carpetas configuradas"
                                    color: MichiTheme.colors.textSecondary
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                            }
                        }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm
>>>>>>> Stashed changes

                        MichiButton {
                            id: addFolderBtn
                            text: "Añadir carpeta de música"
                            variant: "primary"
<<<<<<< Updated upstream
=======
                            Accessible.name: "Añadir carpeta musical"
                            KeyNavigation.tab: watchSwitch
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            id: rescanBtn
                            objectName: "settings.library.rescan"
                            text: "Reescanear"
                            variant: "secondary"
                            Accessible.name: "Reescanear biblioteca"
                            KeyNavigation.tab: clearRescanBtn
=======

                        MichiButton {
                            id: addFolderBtn
                            text: "Añadir carpeta de música"
                            variant: "primary"
>>>>>>> Stashed changes
                            Layout.fillWidth: true
                            onClicked: folderDialog.open()
                            Accessible.name: "Añadir carpeta de música"
                        }
                    }
                }

                GlassCard {
                    id: scanningCard
                    Layout.fillWidth: true
                    title: "Escaneo"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
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
                                id: watchChanges
                                objectName: "settings.library.watchChanges"
                                checked: root._loadValue("library/watch_changes", true)
                                onClicked: root._saveValue("library/watch_changes", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Vigilar cambios en carpetas"
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
                                id: autoScan
                                objectName: "settings.library.autoScan"
                                checked: root._loadValue("library/auto_scan", true)
                                onClicked: root._saveValue("library/auto_scan", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Escanear al iniciar"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
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
                                id: indexerMode
                                objectName: "settings.library.indexerMode"
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
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Modo de indexación"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: coversCard
                    Layout.fillWidth: true
                    title: "Carátulas"
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
                                id: coverArtMode
                                objectName: "settings.library.coverArtMode"
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
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Extracción de carátulas"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: enrichmentCard
                    Layout.fillWidth: true
                    title: "Enriquecimiento de metadatos"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
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
                                id: metadataEnrichment
                                objectName: "settings.library.metadataEnrichment"
                                checked: root._loadValue("artist_enrichment/enabled", false)
                                onClicked: root._saveValue("artist_enrichment/enabled", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Enriquecimiento automático"
                                Accessible.description: "Obtener metadatos de MusicBrainz y otras fuentes"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: maintenanceCard
                    Layout.fillWidth: true
                    title: "Mantenimiento"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            text: "Reescanear biblioteca"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._rescanLibrary()
                            Accessible.name: "Reescanear biblioteca"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Limpiar y reescanear biblioteca"
                            variant: "danger"
                            Layout.fillWidth: true
                            onClicked: confirmRescan.open()
                            Accessible.name: "Limpiar y reescanear biblioteca"
                            Accessible.description: "Elimina la base de datos y reescanea desde cero"
=======
                            KeyNavigation.tab: clearRescanBtn
=======

                        MichiButton {
                            id: addFolderBtn
                            text: "Añadir carpeta de música"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: folderDialog.open()
                            Accessible.name: "Añadir carpeta de música"
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
                Item { Layout.fillHeight: true }
=======
                GlassCard {
                    id: scanningCard
                    Layout.fillWidth: true
                    title: "Escaneo"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
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
                                id: watchChanges
                                objectName: "settings.library.watchChanges"
                                checked: root._loadValue("library/watch_changes", true)
                                onClicked: root._saveValue("library/watch_changes", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Vigilar cambios en carpetas"
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
                                id: autoScan
                                objectName: "settings.library.autoScan"
                                checked: root._loadValue("library/auto_scan", true)
                                onClicked: root._saveValue("library/auto_scan", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Escanear al iniciar"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
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
                                id: indexerMode
                                objectName: "settings.library.indexerMode"
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
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Modo de indexación"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: coversCard
                    Layout.fillWidth: true
                    title: "Carátulas"
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
                                id: coverArtMode
                                objectName: "settings.library.coverArtMode"
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
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Extracción de carátulas"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: enrichmentCard
                    Layout.fillWidth: true
                    title: "Enriquecimiento de metadatos"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
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
                                id: metadataEnrichment
                                objectName: "settings.library.metadataEnrichment"
                                checked: root._loadValue("artist_enrichment/enabled", false)
                                onClicked: root._saveValue("artist_enrichment/enabled", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Enriquecimiento automático"
                                Accessible.description: "Obtener metadatos de MusicBrainz y otras fuentes"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: maintenanceCard
                    Layout.fillWidth: true
                    title: "Mantenimiento"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            text: "Reescanear biblioteca"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._rescanLibrary()
                            Accessible.name: "Reescanear biblioteca"
=======
>>>>>>> Stashed changes
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Limpiar y reescanear biblioteca"
                            variant: "danger"
                            Layout.fillWidth: true
                            onClicked: confirmRescan.open()
                            Accessible.name: "Limpiar y reescanear biblioteca"
                            Accessible.description: "Elimina la base de datos y reescanea desde cero"
>>>>>>> origin/michi-qml-functional-wave
                        }
                    }
                }

<<<<<<< HEAD
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Escaneo automático"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Vigilar cambios en carpetas"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: watchSwitch
                            objectName: "settings.library.watchFolders"
                            checked: true
                            Accessible.name: "Vigilar cambios en carpetas"
                            Accessible.description: "Detectar cambios automáticamente"
                            KeyNavigation.tab: autoScanSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Escaneo automático al iniciar"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: autoScanSwitch
                            objectName: "settings.library.autoScan"
                            checked: true
                            Accessible.name: "Escaneo automático al iniciar"
                            KeyNavigation.tab: indexerModeCombo
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Modo de indexación"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: indexerModeCombo
                            objectName: "settings.library.indexerMode"
                            model: ["Rápido", "Completo", "Profundo"]
                            currentIndex: 1
                            Accessible.name: "Modo de indexación"
                            KeyNavigation.tab: coverArtSwitch
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Carátulas y metadatos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Extraer carátulas incrustadas"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: coverArtSwitch
                            objectName: "settings.library.coverArtExtraction"
                            checked: true
                            Accessible.name: "Extraer carátulas incrustadas"
                            KeyNavigation.tab: metadataEnrichmentSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Enriquecimiento de metadatos"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: metadataEnrichmentSwitch
                            objectName: "settings.library.metadataEnrichment"
                            checked: true
                            Accessible.name: "Enriquecimiento de metadatos"
                            Accessible.description: "Completar metadatos desde fuentes externas"
                            KeyNavigation.tab: addFolderBtn
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
                        text: "Acciones destructivas"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Text {
                        text: "Estas acciones no se pueden deshacer."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }

                    MichiButton {
                        id: clearRescanBtn
                        objectName: "settings.library.clearAndRescan"
                        text: "Limpiar y reescanear"
                        variant: "danger"
                        Accessible.name: "Limpiar y reescanear biblioteca"
                        Accessible.description: "Elimina todos los datos indexados y vuelve a escanear. Acción destructiva."
                        KeyNavigation.tab: addFolderBtn
                        onClicked: confirmClearRescanDialog.open()
                    }
                }
=======
                Item { Layout.fillHeight: true }
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            }
        }
    }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    FolderDialog {
        id: folderDialog
        title: "Seleccionar carpeta de música"
        onAccepted: {
            var folderPath = folder.toString().replace("file://", "")
            if (folderPath) root._addFolder(folderPath)
        }
    }
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    ConfirmActionDialog {
        id: confirmClearRescanDialog
        objectName: "settings.library.clearRescanConfirm"
        title: "Limpiar y reescanear"
        message: "¿Estás seguro? Esto eliminará todos los datos indexados de la biblioteca y volverá a escanear todas las carpetas. Esta acción no se puede deshacer."
        confirmText: "Limpiar y reescanear"
        danger: true
        onConfirmed: {
            console.log("[Settings] Limpiar y reescanear biblioteca")
        }
    }
=======
    FolderDialog {
        id: folderDialog
        title: "Seleccionar carpeta de música"
        onAccepted: {
            var folderPath = folder.toString().replace("file://", "")
            if (folderPath) root._addFolder(folderPath)
        }
    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    ConfirmActionDialog {
        id: confirmRescan
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
