import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Drawer {
    id: root

    property var bridge: null

    property var _typeFilters: {
        "track": true,
        "album": true,
        "artist": true,
        "playlist": true,
        "folder": true,
        "genre": true,
        "radio": true,
        "device": false,
        "server": false,
        "action": false,
        "setting": false,
    }
    property int _yearFrom: 0
    property int _yearTo: 0
    property string _qualityFilter: "any"

    signal filtersApplied(var typeFilters, int yearFrom, int yearTo, string quality)
    signal filtersReset()

    edge: Qt.RightEdge
    width: Math.min(parent.width * 0.35, 320)
    height: parent.height
    modal: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    objectName: "searchFiltersDrawer"
    Accessible.role: Accessible.Dialog
    Accessible.name: "Filtros de búsqueda"
    Accessible.description: "Filtrar resultados por tipo, año y calidad"

    background: Rectangle {
        color: MichiTheme.colors.surfacePopup
        border.color: MichiTheme.colors.borderCard
        border.width: 1
    }

    Column {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Text {
                text: qsTr("Filtros")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: parent.width - 120; height: 1 }
    focus: true

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: qsTr("Cerrar")
                variant: "ghost"
                anchors.verticalCenter: parent.verticalCenter
                onClicked: root.close()
                Keys.onEscapePressed: root.close()
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: qsTr("Tipo de resultado")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.xs

            Repeater {
                model: [
                    {key: qsTr("track"), label: "Canciones"},
                    {key: qsTr("album"), label: "Álbumes"},
                    {key: qsTr("artist"), label: "Artistas"},
                    {key: qsTr("playlist"), label: "Playlists"},
                    {key: qsTr("folder"), label: "Carpetas"},
                    {key: qsTr("genre"), label: "Géneros"},
                    {key: qsTr("radio"), label: "Radio"},
                    {key: qsTr("device"), label: "Dispositivos"},
                    {key: qsTr("server"), label: "Servidores"},
                    {key: qsTr("action"), label: "Acciones"},
                    {key: qsTr("setting"), label: "Ajustes"},
                ]

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm
                        Accessible.role: Accessible.CheckBox

                        Accessible.name: "CheckBox"

                        Accessible.checked: root.checked

                        activeFocusOnTab: true


                    CheckBox {
                        id: typeCheck
                        checked: root._typeFilters[modelData.key] !== false

                        onCheckedChanged: root._typeFilters[modelData.key] = checked

                        indicator: Rectangle {
                            x: typeCheck.leftPadding
                            y: parent.height / 2 - height / 2
                            width: 18
                            height: 18
                            radius: MichiTheme.radius.xs
                            color: typeCheck.checked ? MichiTheme.colors.accent : "transparent"
                            border.color: typeCheck.checked ? MichiTheme.colors.accent : MichiTheme.colors.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: qsTr("\u2713")
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: MichiTheme.typography.metaSize
                                visible: typeCheck.checked
                            }
                        }

                        contentItem: Text {
                            text: modelData.label
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            leftPadding: typeCheck.indicator.width + typeCheck.spacing
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: qsTr("Rango de año")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiSearchField {
                id: yearFromField
                width: parent.width * 0.45
                placeholderText: qsTr("Desde")
                text: root._yearFrom > 0 ? String(root._yearFrom) : ""
                onSearchTextChanged: root._yearFrom = parseInt(text) || 0
            }

            Text {
                text: qsTr("\u2013")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }

            MichiSearchField {
                id: yearToField
                width: parent.width * 0.45
                placeholderText: qsTr("Hasta")
                text: root._yearTo > 0 ? String(root._yearTo) : ""
                onSearchTextChanged: root._yearTo = parseInt(text) || 0
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: qsTr("Calidad")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    {key: qsTr("any"), label: "Cualquiera"},
                    {key: qsTr("low"), label: "Baja"},
                    {key: qsTr("standard"), label: "Estándar"},
                    {key: qsTr("high"), label: "Alta"},
                    {key: qsTr("lossless"), label: "Lossless"},
                ]

                MichiButton {
                    text: modelData.label
                    variant: root._qualityFilter === modelData.key ? "primary" : "ghost"
                    implicitHeight: 28
                    onClicked: root._qualityFilter = modelData.key
                }
            }
        }

        Item { width: 1; height: MichiTheme.spacing.md }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: qsTr("Aplicar filtros")
                variant: "primary"
                onClicked: {
                    root.filtersApplied(root._typeFilters, root._yearFrom, root._yearTo, root._qualityFilter)
                    root.close()
                }
            }

            MichiButton {
                text: qsTr("Restablecer")
                variant: "ghost"
                onClicked: {
                    root._typeFilters = {
                        "track": true, "album": true, "artist": true,
                        "playlist": true, "folder": true, "genre": true,
                        "radio": true, "device": false, "server": false,
                        "action": false, "setting": false
                    }
                    root._yearFrom = 0
                    root._yearTo = 0
                    root._qualityFilter = "any"
                    yearFromField.text = ""
                    yearToField.text = ""
                    root.filtersReset()
                }
            }
        }
    }
}
