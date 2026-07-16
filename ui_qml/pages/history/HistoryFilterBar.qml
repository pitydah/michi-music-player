import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "History Filter Bar"
    objectName: "historyFilterBar"
    focus: true
    id: root

    property string artistFilter: ""
    property string albumFilter: ""
    property string deviceFilter: ""
    property string searchText: ""
    property bool dateRangeEnabled: false
    property date dateFrom: new Date(0)
    property date dateTo: new Date()

    signal filtersChanged()
    signal clearFilters()

    implicitHeight: _filterLayout.height

    function reset() {
        artistFilter = ""
        albumFilter = ""
        deviceFilter = ""
        searchText = ""
        dateRangeEnabled = false
        dateFrom = new Date(0)
        dateTo = new Date()
        searchField.text = ""
        artistField.text = ""
        albumField.text = ""
        deviceField.text = ""
        dateRangeCheck.checked = false
        fromDateField.text = ""
        toDateField.text = ""
        root.filtersChanged()
    }

    Column {
        id: _filterLayout
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Row {
            spacing: MichiTheme.spacing.sm
            width: parent.width

            SearchField {
                id: searchField
                width: 200
                placeholderText: "Buscar en historial..."
                objectName: "historySearchField"
                Accessible.name: "Buscar en historial"
                onSearchTextChanged: { root.searchText = text; root.filtersChanged() }
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: artistField
                width: 140
                placeholderText: "Artista"
                objectName: "artistFilterField"
                Accessible.name: "Filtrar por artista"
                onTextChanged: { root.artistFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.artistFilter = ""; root.filtersChanged() }
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: albumField
                width: 140
                placeholderText: "Álbum"
                objectName: "albumFilterField"
                Accessible.name: "Filtrar por álbum"
                onTextChanged: { root.albumFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.albumFilter = ""; root.filtersChanged() }
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                id: deviceField
                width: 120
                placeholderText: "Dispositivo"
                objectName: "deviceFilterField"
                Accessible.name: "Filtrar por dispositivo"
                onTextChanged: { root.deviceFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.deviceFilter = ""; root.filtersChanged() }
            }

            MichiButton {
                text: "Limpiar filtros"
                variant: "ghost"
                objectName: "clearFiltersButton"
                Accessible.name: "Limpiar filtros"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.reset()
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
            CheckBox {
                id: dateRangeCheck
                text: "Rango de fecha"
                objectName: "dateRangeCheck"
                Accessible.name: "Activar rango de fecha"
                onCheckedChanged: {
                    root.dateRangeEnabled = checked
                    root.filtersChanged()
                }
            }
            Label {
                text: "Desde:"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
                visible: root.dateRangeEnabled
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: fromDateField
                width: 140
                placeholderText: "YYYY-MM-DD"
                visible: root.dateRangeEnabled
                objectName: "dateFromField"
                Accessible.name: "Fecha desde"
                onTextChanged: {
                    var d = Date.fromLocaleString(Qt.locale(), text, "yyyy-MM-dd")
                    root.dateFrom = d || new Date(0)
                    root.filtersChanged()
                }
                Keys.onEscapePressed: { text = ""; root.filtersChanged() }
            }
            Label {
                text: "Hasta:"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
                visible: root.dateRangeEnabled
            }
            TextField {
                focusPolicy: Qt.StrongFocus
                id: toDateField
                width: 140
                placeholderText: "YYYY-MM-DD"
                visible: root.dateRangeEnabled
                objectName: "dateToField"
                Accessible.name: "Fecha hasta"
                onTextChanged: {
                    var d = Date.fromLocaleString(Qt.locale(), text, "yyyy-MM-dd")
                    root.dateTo = d || new Date()
                    root.filtersChanged()
                }
                Keys.onEscapePressed: { text = ""; root.filtersChanged() }
            }
        }
    }
}
