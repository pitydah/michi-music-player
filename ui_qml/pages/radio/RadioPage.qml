import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    objectName: "radioPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Radio"

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
    property int pageState: stateReady

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

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

    Component.onCompleted: {
        if (root.rd && typeof root.rd.refresh !== "undefined")
            root.rd.refresh()
        radioGuard.checkCapability(root.rd)
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: "Cargando emisoras" }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: Component {
            Rectangle {
                anchors.centerIn: parent
                width: 480
                height: 320
                radius: MichiTheme.radius.lg
                color: MichiTheme.colors.surfaceCard
                border.width: 1; border.color: MichiTheme.colors.borderCard

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    width: parent.width - MichiTheme.spacing.xl * 2

                    Text { text: "RD"; font.pixelSize: 36; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: "Radio no disponible"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: "Explora emisoras de todo el mundo, descubre nueva musica y guarda tus favoritas. Necesitas una suscripcion premium para acceder al catalogo completo de emisoras y transmision sin interrupciones."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; width: parent.width }
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm
                        MichiButton { text: "Configurar"; variant: "primary"; onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("settings") } }
                        MichiButton { text: "Ver requisitos"; variant: "ghost"; onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("settings") } }
                    }
                }
            }
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: "Sin emisoras"; subtitle: "Agrega emisoras para empezar a escuchar" }
    }

    RadioEditDialog {
        id: editDialog
        parent: root
        anchors.centerIn: parent
        modal: true
        onClosed: {
            if (root.rd && typeof root.rd.refresh === "function")
                root.rd.refresh()
        }
    }

    CapabilityGuard {
        id: radioGuard
        anchors.fill: parent
        capabilityName: "radio"
        visible: root.pageState === root.stateReady

        Flickable {
            id: flickable
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true; boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column; width: parent.width; spacing: MichiTheme.spacing.lg

                HeroMaterial {
                    id: radioHero
                    width: parent.width; height: 140; radius: MichiTheme.radius.lg; showGlow: true
                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                        Text {
                            text: "Radio"; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                        }
                        Text {
                            text: "Emisoras de todo el mundo."; color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                        }
                        StatusBadge {
                            text: root._buffering ? "Buffering..." : ""
                            kind: "warning"
                            visible: root._buffering
                        }
                    }
                }

                MichiSearchField {
                    id: radioSearch
                    width: parent.width
                    placeholderText: "Buscar emisoras..."
                    onSearchTextChanged: root.doSearch(text)
                    KeyNavigation.tab: favoritesSection
                    KeyNavigation.backtab: flickable
                }

                SectionHeader {
                    id: favoritesSection
                    text: "Favoritas"
                    width: parent.width
                }

                Repeater {
                    model: root.rd ? root.rd.favorites : []

                    RadioStationDetail {
                        width: parent.width
                        stationData: modelData
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onPlayRequested()
                        Keys.onSpacePressed: onPlayRequested()
                        onPlayRequested: root.playStation(modelData.url)
                        onToggleFavRequested: {
                            var sid = modelData.id || 0
                            if (sid > 0) root.toggleFavorite(sid)
                        }
                        onEditRequested: {
                            root._activeDetailId = index
                            editDialog.stationData = modelData
                            editDialog.radioBridge = root.rd
                            editDialog.open()
                        }
                        onDeleteRequested: root.deleteStation(modelData.url)
                    }
                }

                Text {
                    text: "No hay emisoras favoritas."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width; wrapMode: Text.WordWrap
                    visible: root.rd && root.rd.favorites.length === 0
                }

                SectionHeader {
                    id: allStationsHeader
                    text: "Todas las emisoras"
                    width: parent.width
                }

                Repeater {
                    model: root.rd ? root.rd.stations : []

                    RadioStationDetail {
                        width: parent.width
                        stationData: modelData
                        activeFocusOnTab: true
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
                            root._activeDetailId = index
                            editDialog.stationData = modelData
                            editDialog.radioBridge = root.rd
                            editDialog.open()
                        }
                        onDeleteRequested: root.deleteStation(modelData.url)
                    }
                }

                Text {
                    text: root._filterText !== ""
                          ? "No se encontraron emisoras para \"" + root._filterText + "\""
                          : "No hay emisoras configuradas."
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width; wrapMode: Text.WordWrap
                    visible: root.rd && root.rd.stations.length === 0
                }

                MichiButton {
                    id: addStationBtn
                    objectName: "addStationToggleButton"
                    text: _showAddStation ? "Cancelar" : "Añadir emisora"
                    variant: "ghost"
                    anchors.horizontalCenter: parent.horizontalCenter
                    activeFocusOnTab: true
                    KeyNavigation.tab: addStationForm
                    KeyNavigation.backtab: allStationsHeader
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: _showAddStation = !_showAddStation
                }

                Column {
                    id: addStationForm
                    width: parent.width; spacing: MichiTheme.spacing.sm
                    visible: _showAddStation

                    Rectangle { width: parent.width; height: 1; color: MichiTheme.colors.borderSubtle }

                    MichiSearchField {
                        placeholderText: "Nombre"; width: parent.width; onSearchTextChanged: _newName = text
                    }

                    MichiSearchField {
                        placeholderText: "URL del stream"; width: parent.width; onSearchTextChanged: _newUrl = text
                    }
                    MichiSearchField {
                        placeholderText: "Codec (MP3, AAC, ...)"; width: parent.width; onSearchTextChanged: _newCodec = text
                    }
                    MichiSearchField {
                        placeholderText: "País"; width: parent.width; onSearchTextChanged: _newCountry = text
                    }
                    MichiButton {
                        objectName: "addStationSubmitButton"
                        text: "Añadir"; variant: "primary"
                        anchors.horizontalCenter: parent.horizontalCenter
                        activeFocusOnTab: true
                        Keys.onReturnPressed: onClicked()
                        Keys.onSpacePressed: onClicked()
                        onClicked: addStationFromUI()
                    }
                }

                SectionHeader {
                    id: historySection
                    text: "Historial reciente"
                    width: parent.width
                }
                Repeater {
                    model: root.rd && typeof root.rd.history !== "undefined" ? root.rd.history : []
                    delegate: Text {
                        width: parent.width
                        text: (modelData.name || modelData.url || "") + " — " + (modelData.played_at || "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        elide: Text.ElideRight
                    }
                }

                StatusBadge {
                    id: radioStatusBadge
                    text: "Radio QML — " + (root.rd && root.rd.stations ? root.rd.stations.length + " emisoras" : "0 emisoras")
                    kind: "info"
                }
            }
        }
    }
}
