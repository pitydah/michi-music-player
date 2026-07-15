import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _filterText: ""
    property bool _showAddStation: false
    property string _newName: ""
    property string _newUrl: ""
    property string _newCodec: "MP3"
    property string _newCountry: ""
    property int _activeDetailId: -1
    property bool _buffering: false
    property bool _showImportDialog: false
    property bool _showEditorDialog: false
    property var _editorStationData: null

    objectName: "radio.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Radio"
    Accessible.description: "Emisoras de radio de todo el mundo"

    function doSearch(text) {
        _filterText = text.toLowerCase()
    }

    function addStationFromUI() {
        if (root.rd && _newUrl.trim()) {
            var result = root.rd.addStation(
                _newName.trim() || "New station", _newUrl.trim(),
                _newCodec, _newCountry
            )
            if (result && result.ok) {
                _newName = ""; _newUrl = ""; _newCodec = "MP3"; _newCountry = ""
                _showAddStation = false
                if (root.notif) root.notif.showMessage("Emisora añadida", "success")
            } else {
                if (root.notif) root.notif.showMessage("Error: " + (result ? result.error : "desconocido"), "error")
            }
        }
    }

    function toggleFavorite(stationId) {
        if (root.rd && typeof root.rd.toggleFavorite === "function") {
            var r = root.rd.toggleFavorite(stationId)
            if (r.ok && root.notif)
                root.notif.showMessage(r.favorite ? "Añadida a favoritos" : "Eliminada de favoritos", "info")
            else if (!r.ok && root.notif)
                root.notif.showMessage(r.error, "error")
        }
    }

    function playStation(url) {
        if (root.rd && typeof root.rd.playStation === "function") {
            _buffering = true
            var r = root.rd.playStation(url)
            if (!r.ok && root.notif)
                root.notif.showMessage("Error al reproducir: " + r.error, "error")
        }
    }

    function deleteStation(url) {
        if (root.rd && typeof root.rd.deleteStation === "function") {
            var r = root.rd.deleteStation(url)
            if (r.ok && root.notif) root.notif.showMessage("Emisora eliminada", "success")
            else if (!r.ok && root.notif) root.notif.showMessage(r.error, "error")
        }
    }

    function stopStream() {
        if (root.rd && typeof root.rd.stopStream === "function") {
            root.rd.stopStream()
            _buffering = false
        }
    }

    function openEditor(stationData) {
        root._editorStationData = stationData
        root._showEditorDialog = true
    }

    function openImportDialog() {
        root._showImportDialog = true
    }

    Component.onCompleted: {
        if (root.rd && typeof root.rd.refresh !== "undefined")
            root.rd.refresh()
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "radio.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (root._showAddStation) root._showAddStation = false
            else if (root._showEditorDialog) root._showEditorDialog = false
            else if (root._showImportDialog) root._showImportDialog = false
        }

        Flickable {
            id: flickable
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "radio.flickableContent"

            Keys.onEscapePressed: {
                if (root._showAddStation) root._showAddStation = false
                else if (root._showEditorDialog) root._showEditorDialog = false
                else if (root._showImportDialog) root._showImportDialog = false
            }

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: hero
                    width: parent.width
                    height: 140
                    radius: MichiTheme.radiusLg
                    showGlow: true
                    objectName: "radio.hero"

                    Column {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.xl
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Radio"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                            Accessible.role: Accessible.Heading
                            Accessible.name: "Radio"
                        }

                        Text {
                            text: "Emisoras de todo el mundo."
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width * 0.70
                            wrapMode: Text.WordWrap
                        }

                        StatusBadge {
                            text: {
                                if (!root.rd) return "Servicio no disponible"
                                if (root._buffering) return "Buffering..."
                                return "Listo"
                            }
                            kind: root._buffering ? "warning" : "info"
                            visible: true
                            objectName: "radio.statusBadge"
                        }
                    }
                }

                SearchField {
                    id: searchField
                    width: parent.width
                    placeholderText: "Buscar emisoras..."
                    onSearchTextChanged: root.doSearch(text)
                    objectName: "radio.searchField"
                    Accessible.name: "Buscar emisoras"
                    KeyNavigation.tab: toolbarRow
                }

                Row {
                    id: toolbarRow
                    width: parent.width
                    spacing: MichiTheme.spacing.sm
                    objectName: "radio.toolbarRow"

                    MichiButton {
                        text: root._showAddStation ? "Cancelar" : "Añadir emisora"
                        variant: "ghost"
                        onClicked: root._showAddStation = !root._showAddStation
                        objectName: "radio.toolbar.addStation"
                        Accessible.name: root._showAddStation ? "Cancelar añadir emisora" : "Añadir emisora"
                        KeyNavigation.tab: importButton
                        KeyNavigation.backtab: searchField
                    }

                    MichiButton {
                        id: importButton
                        text: "Importar"
                        variant: "ghost"
                        onClicked: root.openImportDialog()
                        objectName: "radio.toolbar.import"
                        Accessible.name: "Importar emisoras desde archivo"
                        KeyNavigation.tab: stopButton
                        KeyNavigation.backtab: addStationBtn
                    }

                    MichiButton {
                        id: stopButton
                        text: "\u23F9 Detener"
                        variant: "danger"
                        enabled: root._buffering
                        onClicked: root.stopStream()
                        objectName: "radio.toolbar.stop"
                        Accessible.name: "Detener reproducción"
                        KeyNavigation.tab: favoritesSection
                        KeyNavigation.backtab: importButton
                    }
                }

                Column {
                    id: addStationForm
                    width: parent.width
                    spacing: MichiTheme.spacing.sm
                    visible: root._showAddStation
                    objectName: "radio.addStationForm"

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: MichiTheme.colors.borderSubtle
                    }

                    SearchField {
                        placeholderText: "Nombre"
                        width: parent.width
                        onTextChangedByUser: root._newName = text
                        objectName: "radio.addStation.name"
                        Accessible.name: "Nombre de la emisora"
                        KeyNavigation.tab: addUrlField
                    }
                    SearchField {
                        id: addUrlField
                        placeholderText: "URL del stream"
                        width: parent.width
                        onTextChangedByUser: root._newUrl = text
                        objectName: "radio.addStation.url"
                        Accessible.name: "URL del stream"
                        KeyNavigation.tab: addCodecField
                    }
                    SearchField {
                        id: addCodecField
                        placeholderText: "Codec (MP3, AAC, ...)"
                        width: parent.width
                        onTextChangedByUser: root._newCodec = text
                        objectName: "radio.addStation.codec"
                        Accessible.name: "Codec de la emisora"
                        KeyNavigation.tab: addCountryField
                    }
                    SearchField {
                        id: addCountryField
                        placeholderText: "País"
                        width: parent.width
                        onTextChangedByUser: root._newCountry = text
                        objectName: "radio.addStation.country"
                        Accessible.name: "País de la emisora"
                        KeyNavigation.tab: addSubmitBtn
                    }
                    MichiButton {
                        id: addSubmitBtn
                        text: "Añadir"
                        variant: "primary"
                        anchors.horizontalCenter: parent.horizontalCenter
                        onClicked: root.addStationFromUI()
                        objectName: "radio.addStation.submit"
                        Accessible.name: "Confirmar añadir emisora"
                        KeyNavigation.tab: searchField
                    }
                }

                Loader {
                    width: parent.width
                    height: active ? parent.height : 0
                    active: !root.rd

                    sourceComponent: UnavailableState {
                        title: "Radio no disponible"
                        message: "El servicio de radio no está disponible en este momento."
                        explanation: "Radio Bridge no está configurado o el módulo no está activo."
                        objectName: "radio.unavailableState"
                    }
                }

                Loader {
                    width: parent.width
                    height: active ? childrenRect.height : 0
                    active: root.rd

                    sourceComponent: Column {
                        width: parent.width
                        spacing: MichiTheme.spacing.lg

                        SectionHeader {
                            id: favoritesSection
                            text: "Favoritas (" + (root.rd ? root.rd.favorites.length : 0) + ")"
                            width: parent.width
                            objectName: "radio.section.favorites"
                            Accessible.name: "Sección de emisoras favoritas"
                            KeyNavigation.tab: favoritesRepeater
                            KeyNavigation.backtab: stopButton
                        }

                        Repeater {
                            id: favoritesRepeater
                            model: root.rd ? root.rd.favorites : []
                            objectName: "radio.list.favorites"

                            RadioStationDetail {
                                width: parent.width
                                stationData: modelData
                                objectName: "radio.station.favorite." + index
                                onPlayRequested: root.playStation(modelData.url)
                                onToggleFavRequested: {
                                    var sid = modelData.id || 0
                                    if (sid > 0) root.toggleFavorite(sid)
                                }
                                onEditRequested: {
                                    root.openEditor(modelData)
                                }
                                onDeleteRequested: root.deleteStation(modelData.url)
                                KeyNavigation.tab: index < root.rd.favorites.length - 1
                                    ? favoritesRepeater.itemAt(index + 1)
                                    : allStationsSection
                            }
                        }

                        Text {
                            id: emptyFavoritesText
                            text: "No hay emisoras favoritas."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width
                            wrapMode: Text.WordWrap
                            visible: root.rd && root.rd.favorites.length === 0
                            objectName: "radio.empty.favorites"
                        }

                        SectionHeader {
                            id: allStationsSection
                            text: "Todas las emisoras (" + (root.rd ? root.rd.stations.length : 0) + ")"
                            width: parent.width
                            objectName: "radio.section.allStations"
                            Accessible.name: "Sección de todas las emisoras"
                            KeyNavigation.tab: allStationsRepeater
                            KeyNavigation.backtab: favoritesRepeater
                        }

                        Repeater {
                            id: allStationsRepeater
                            model: root.rd ? root.rd.stations : []
                            objectName: "radio.list.allStations"

                            RadioStationDetail {
                                width: parent.width
                                stationData: modelData
                                objectName: "radio.station." + index
                                visible: {
                                    if (root._filterText === "") return true
                                    var name = (modelData.name || "").toLowerCase()
                                    var tags = (modelData.tags || []).join(" ").toLowerCase()
                                    var country = (modelData.country || "").toLowerCase()
                                    return name.indexOf(root._filterText) >= 0
                                        || tags.indexOf(root._filterText) >= 0
                                        || country.indexOf(root._filterText) >= 0
                                }
                                onPlayRequested: root.playStation(modelData.url)
                                onToggleFavRequested: {
                                    var sid = modelData.id || 0
                                    if (sid > 0) root.toggleFavorite(sid)
                                }
                                onEditRequested: {
                                    root.openEditor(modelData)
                                }
                                onDeleteRequested: root.deleteStation(modelData.url)
                            }
                        }

                        Text {
                            id: emptyStationsText
                            text: root._filterText !== ""
                                  ? "No se encontraron emisoras para \"" + root._filterText + "\""
                                  : "No hay emisoras configuradas."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            width: parent.width
                            wrapMode: Text.WordWrap
                            visible: root.rd && root.rd.stations.length === 0
                            objectName: "radio.empty.stations"
                        }

                        SectionHeader {
                            id: historySection
                            text: "Historial reciente"
                            width: parent.width
                            objectName: "radio.section.history"
                            Accessible.name: "Sección de historial reciente"
                        }

                        Repeater {
                            model: root.rd && typeof root.rd.history !== "undefined" ? root.rd.history : []
                            delegate: Text {
                                width: parent.width
                                text: (modelData.name || modelData.url || "") + " \u2014 " + (modelData.played_at || "")
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                                elide: Text.ElideRight
                            }
                        }

                        StatusBadge {
                            text: "Radio QML \u2014 " + (root.rd && root.rd.stations ? root.rd.stations.length + " emisoras" : "0 emisoras")
                            kind: "info"
                            objectName: "radio.statusBadge"
                        }
                    }
                }
            }
        }
    }

    RadioEditorDialog {
        id: editorDialog
        parent: root
        rd: root.rd
        stationData: root._editorStationData
        visible: root._showEditorDialog
        onOpened: {}
        onClosed: {
            root._showEditorDialog = false
            root._editorStationData = null
        }
    }

    RadioImportDialog {
        id: importDialog
        parent: root
        rd: root.rd
        notif: root.notif
        visible: root._showImportDialog
        onClosed: {
            root._showImportDialog = false
        }
    }
}
