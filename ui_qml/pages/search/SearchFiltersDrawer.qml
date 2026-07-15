import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property bool open: false
    property var bridge: null
    property var _typeFilters: ({})
    property int _yearFrom: 0
    property int _yearTo: 0
    property string _qualityFilter: ""

    signal applied(var filters)
    signal reset()

    objectName: "searchFiltersDrawer"
    visible: open

    Accessible.role: Accessible.Dialog
    Accessible.name: "Filtros de búsqueda"

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceOverlay

        MouseArea {
            anchors.fill: parent
            onClicked: root.open = false
        }
    }

    Rectangle {
        id: drawer
        width: 300
        height: parent.height
        anchors.right: parent.right
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Filtros"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightBold
                Accessible.role: Accessible.Heading
                Accessible.name: "Filtros de búsqueda"
            }

            SectionHeader {
                text: "Tipo de resultado"
                width: parent.width
            }

            Column {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Repeater {
                    model: ["track", "album", "artist", "playlist", "folder", "genre", "radio", "device", "server", "action", "setting"]

                    CheckBox {
                        id: cb
                        text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                        checked: root._typeFilters[modelData] !== false
                        onCheckedChanged: root._typeFilters[modelData] = checked
                        objectName: "searchFilter.type." + modelData
                        Accessible.name: "Filtrar por " + text
                    }
                }
            }

            SectionHeader {
                text: "Año"
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                TextField {
                    id: yearFromField
                    width: parent.width * 0.45
                    placeholderText: "Desde"
                    validator: IntValidator { bottom: 1900; top: 2100 }
                    onTextChanged: root._yearFrom = parseInt(text) || 0
                    objectName: "searchFilter.yearFrom"
                    Accessible.name: "Año desde"
                }

                Text {
                    text: "-"
                    color: MichiTheme.colors.textMuted
                    anchors.verticalCenter: parent.verticalCenter
                }

                TextField {
                    id: yearToField
                    width: parent.width * 0.45
                    placeholderText: "Hasta"
                    validator: IntValidator { bottom: 1900; top: 2100 }
                    onTextChanged: root._yearTo = parseInt(text) || 0
                    objectName: "searchFilter.yearTo"
                    Accessible.name: "Año hasta"
                }
            }

            SectionHeader {
                text: "Calidad"
                width: parent.width
            }

            ComboBox {
                id: qualityCombo
                width: parent.width
                model: ["Cualquiera", "≥ 128 kbps", "≥ 192 kbps", "≥ 320 kbps", "FLAC / Lossless"]
                onCurrentTextChanged: {
                    var map = {
                        "Cualquiera": "", "≥ 128 kbps": "128",
                        "≥ 192 kbps": "192", "≥ 320 kbps": "320",
                        "FLAC / Lossless": "lossless"
                    }
                    root._qualityFilter = map[currentText] || ""
                }
                objectName: "searchFilter.quality"
                Accessible.name: "Filtro de calidad"
            }

            Item { height: MichiTheme.spacing.sm; width: 1 }

            Row {
                spacing: MichiTheme.spacing.md
                anchors.horizontalCenter: parent.horizontalCenter

                MichiButton {
                    text: "Aplicar"
                    variant: "primary"
                    onClicked: {
                        root.applied({
                            typeFilters: root._typeFilters,
                            yearFrom: root._yearFrom,
                            yearTo: root._yearTo,
                            quality: root._qualityFilter
                        })
                        root.open = false
                    }
                    objectName: "searchFilter.apply"
                    Accessible.name: "Aplicar filtros"
                }

                MichiButton {
                    text: "Restablecer"
                    variant: "ghost"
                    onClicked: {
                        root._typeFilters = {}
                        root._yearFrom = 0
                        root._yearTo = 0
                        root._qualityFilter = ""
                        root.reset()
                    }
                    objectName: "searchFilter.reset"
                    Accessible.name: "Restablecer filtros"
                }
            }
        }
    }
}
