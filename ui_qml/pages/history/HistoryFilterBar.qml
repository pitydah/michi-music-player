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
                Accessible.role: Accessible.EditableText

                id: searchField
                activeFocusOnTab: true

                width: 200
                placeholderText: "Buscar en historial..."
                onSearchTextChanged: { root.searchText = text; root.filtersChanged() }
            }
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true


            TextField {
                focusPolicy: Qt.StrongFocus
                id: artistField
                width: 140
                placeholderText: "Artista"
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

                onTextChanged: { root.artistFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.artistFilter = ""; root.filtersChanged() }
            }

            TextField {
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                id: albumField
                activeFocusOnTab: true

                width: 140
                placeholderText: "Álbum"
                onTextChanged: { root.albumFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.albumFilter = ""; root.filtersChanged() }
            }
                Accessible.role: Accessible.Button

                activeFocusOnTab: true


            TextField {
                focusPolicy: Qt.StrongFocus
                id: deviceField
                width: 120
                placeholderText: "Dispositivo"
                onTextChanged: { root.deviceFilter = text.trim(); root.filtersChanged() }
                Keys.onEscapePressed: { text = ""; root.deviceFilter = ""; root.filtersChanged() }
            }

                Accessible.role: Accessible.CheckBox

                Accessible.name: "CheckBox"

                Accessible.checked: root.checked

            MichiButton {
                text: "Limpiar filtros"
                variant: "ghost"
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.reset()
            }
        }

        Row {
            spacing: MichiTheme.spacing.sm
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                activeFocusOnTab: true

            CheckBox {
                id: dateRangeCheck
                text: "Rango de fecha"
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
                Accessible.role: Accessible.EditableText

                Accessible.name: "Campo de texto"

                id: fromDateField
                activeFocusOnTab: true

                width: 140
                placeholderText: "YYYY-MM-DD"
                visible: root.dateRangeEnabled
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
