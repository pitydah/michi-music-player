import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property string _query: ""
    property string _countryFilter: ""
    property string _tagFilter: ""
    property var _results: []

    function search() {
        if (root.rd && typeof root.rd.search === "function") {
            var r = root.rd.search(root._query, root._countryFilter, root._tagFilter)
            if (r.ok) root._results = r.results || []
            else if (root.notif) root.notif.showMessage("Error: " + r.error, "error")
        }
    }

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Buscar emisoras"; width: parent.width }

        SearchField {
            width: parent.width
            placeholderText: "Nombre de emisora..."
            onTextChangedByUser: root._query = text
            onSearchSubmitted: root.search()
        }

        Row {
            spacing: MichiTheme.spacing.sm
            SearchField {
                width: parent.width * 0.45
                placeholderText: "País..."
                onTextChangedByUser: root._countryFilter = text
            }
            SearchField {
                width: parent.width * 0.45
                placeholderText: "Etiqueta..."
                onTextChangedByUser: root._tagFilter = text
            }
        }

        MichiButton {
            text: "Buscar"
            variant: "primary"
            onClicked: root.search()
        }

        Repeater {
            model: root._results

            RadioStationDetail {
                width: parent.width
                stationData: modelData
                onPlayRequested: {
                    if (root.rd && typeof root.rd.playStation === "function")
                        root.rd.playStation(modelData.url)
                }
                onToggleFavRequested: {
                    var sid = modelData.id || 0
                    if (sid > 0 && root.rd && typeof root.rd.toggleFavorite === "function")
                        root.rd.toggleFavorite(sid)
                }
            }
        }

        Text {
            text: root._query !== "" && root._results.length === 0 ? "Sin resultados" : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
            visible: text !== ""
        }
    }
}
