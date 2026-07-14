import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property string artistFilter: ""
    property string albumFilter: ""
    property string deviceFilter: ""
    property string searchText: ""
    property bool dateRangeEnabled: false
    property int dateFrom: 0
    property int dateTo: 0

    signal filtersChanged()
    signal clearFilters()

    implicitHeight: 80

    function reset() {
        artistFilter = ""; albumFilter = ""; deviceFilter = ""
        searchText = ""; dateRangeEnabled = false
        dateFrom = 0; dateTo = 0
        root.filtersChanged()
    }

    Column {
        anchors.fill: parent; spacing: MichiTheme.spacing.sm

        Row {
            spacing: MichiTheme.spacing.sm; width: parent.width

            SearchField {
                id: searchField; width: 200
                placeholderText: "Buscar en historial..."
                onSearchTextChanged: { root.searchText = text; root.filtersChanged() }
            }

            TextField {
                id: artistField; width: 140; placeholderText: "Artista"
                onTextChanged: { root.artistFilter = text.trim(); root.filtersChanged() }
            }

            TextField {
                id: albumField; width: 140; placeholderText: "Álbum"
                onTextChanged: { root.albumFilter = text.trim(); root.filtersChanged() }
            }

            TextField {
                id: deviceField; width: 120; placeholderText: "Dispositivo"
                onTextChanged: { root.deviceFilter = text.trim(); root.filtersChanged() }
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            CheckBox {
                text: "Rango de fecha"; checked: root.dateRangeEnabled
                onCheckedChanged: { root.dateRangeEnabled = checked; root.filtersChanged() }
            }
            Text {
                text: "Desde:"; color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                visible: root.dateRangeEnabled
            }
            TextField {
                width: 100; placeholderText: "timestamp"
                visible: root.dateRangeEnabled
                onTextChanged: root.dateFrom = parseInt(text) || 0
            }
            Text {
                text: "Hasta:"; color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                visible: root.dateRangeEnabled
            }
            TextField {
                width: 100; placeholderText: "timestamp"
                visible: root.dateRangeEnabled
                onTextChanged: root.dateTo = parseInt(text) || 0
            }
            MichiButton { text: "Limpiar filtros"; variant: "ghost"; onClicked: root.reset() }
        }
    }
}
