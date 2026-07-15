import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

<<<<<<< Updated upstream
<<<<<<< Updated upstream
Drawer {
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
Item {
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg
=======
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

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    Column {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.lg
        spacing: MichiTheme.spacing.md

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

            Text {
                text: "Filtros"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                font.weight: MichiTheme.typography.weightBold
                Accessible.role: Accessible.Heading
                Accessible.name: "Filtros de búsqueda"
>>>>>>> Stashed changes
            }

            Item { width: parent.width - 120; height: 1 }

            MichiButton {
                text: "Cerrar"
                variant: "ghost"
                anchors.verticalCenter: parent.verticalCenter
                objectName: "searchFiltersClose"
                Accessible.name: "Cerrar filtros"
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
            text: "Tipo de resultado"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.xs
            objectName: "filterTypeSection"
            Accessible.role: Accessible.Grouping
            Accessible.name: "Filtrar por tipo"

            Repeater {
                model: [
                    {key: "track", label: "Canciones"},
                    {key: "album", label: "Álbumes"},
                    {key: "artist", label: "Artistas"},
                    {key: "playlist", label: "Playlists"},
                    {key: "folder", label: "Carpetas"},
                    {key: "genre", label: "Géneros"},
                    {key: "radio", label: "Radio"},
                    {key: "device", label: "Dispositivos"},
                    {key: "server", label: "Servidores"},
                    {key: "action", label: "Acciones"},
                    {key: "setting", label: "Ajustes"},
                ]

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    CheckBox {
                        id: typeCheck
                        checked: root._typeFilters[modelData.key] !== false
                        objectName: "filterCheck_" + modelData.key
                        Accessible.name: "Filtrar por " + modelData.label
                        Accessible.role: Accessible.CheckBox

                        onCheckedChanged: root._typeFilters[modelData.key] = checked

                        indicator: Rectangle {
                            x: typeCheck.leftPadding
                            y: parent.height / 2 - height / 2
                            width: 18
                            height: 18
                            radius: 3
                            color: typeCheck.checked ? MichiTheme.colors.accent : "transparent"
                            border.color: typeCheck.checked ? MichiTheme.colors.accent : MichiTheme.colors.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "\u2713"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 11
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
            text: "Rango de año"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            SearchField {
                id: yearFromField
                width: parent.width * 0.45
                placeholderText: "Desde"
                objectName: "filterYearFrom"
                Accessible.name: "Año desde"
                text: root._yearFrom > 0 ? String(root._yearFrom) : ""
                onTextChangedByUser: root._yearFrom = parseInt(text) || 0
            }

            Text {
                text: "\u2013"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }

            SearchField {
                id: yearToField
                width: parent.width * 0.45
                placeholderText: "Hasta"
                objectName: "filterYearTo"
                Accessible.name: "Año hasta"
                text: root._yearTo > 0 ? String(root._yearTo) : ""
                onTextChangedByUser: root._yearTo = parseInt(text) || 0
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: "Calidad"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    {key: "any", label: "Cualquiera"},
                    {key: "low", label: "Baja"},
                    {key: "standard", label: "Estándar"},
                    {key: "high", label: "Alta"},
                    {key: "lossless", label: "Lossless"},
                ]

                MichiButton {
                    text: modelData.label
                    variant: root._qualityFilter === modelData.key ? "primary" : "ghost"
                    implicitHeight: 28
                    objectName: "filterQuality_" + modelData.key
                    Accessible.name: "Calidad " + modelData.label + (root._qualityFilter === modelData.key ? " (activo)" : "")
                    onClicked: root._qualityFilter = modelData.key
                }
            }
        }

        Item { width: 1; height: MichiTheme.spacing.md }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Aplicar filtros"
                variant: "primary"
                objectName: "applyFiltersBtn"
                Accessible.name: "Aplicar filtros"
                onClicked: {
                    root.filtersApplied(root._typeFilters, root._yearFrom, root._yearTo, root._qualityFilter)
                    root.close()
                }
            }

            MichiButton {
                text: "Restablecer"
                variant: "ghost"
                objectName: "resetFiltersBtn"
                Accessible.name: "Restablecer filtros"
                onClicked: {
                    root._typeFilters = {
                        "track": true, "album": true, "artist": true,
                        "playlist": true, "folder": true, "genre": true,
                        "radio": true, "device": false, "server": false,
                        "action": false, "setting": false
                    }
<<<<<<< Updated upstream
=======
                    objectName: "searchFilter.reset"
                    Accessible.name: "Restablecer filtros"
=======
                font.weight: MichiTheme.typography.weightSemiBold
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: parent.width - 120; height: 1 }

            MichiButton {
                text: "Cerrar"
                variant: "ghost"
                anchors.verticalCenter: parent.verticalCenter
                objectName: "searchFiltersClose"
                Accessible.name: "Cerrar filtros"
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
            text: "Tipo de resultado"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Column {
            width: parent.width
            spacing: MichiTheme.spacing.xs
            objectName: "filterTypeSection"
            Accessible.role: Accessible.Grouping
            Accessible.name: "Filtrar por tipo"

            Repeater {
                model: [
                    {key: "track", label: "Canciones"},
                    {key: "album", label: "Álbumes"},
                    {key: "artist", label: "Artistas"},
                    {key: "playlist", label: "Playlists"},
                    {key: "folder", label: "Carpetas"},
                    {key: "genre", label: "Géneros"},
                    {key: "radio", label: "Radio"},
                    {key: "device", label: "Dispositivos"},
                    {key: "server", label: "Servidores"},
                    {key: "action", label: "Acciones"},
                    {key: "setting", label: "Ajustes"},
                ]

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    CheckBox {
                        id: typeCheck
                        checked: root._typeFilters[modelData.key] !== false
                        objectName: "filterCheck_" + modelData.key
                        Accessible.name: "Filtrar por " + modelData.label
                        Accessible.role: Accessible.CheckBox

                        onCheckedChanged: root._typeFilters[modelData.key] = checked

                        indicator: Rectangle {
                            x: typeCheck.leftPadding
                            y: parent.height / 2 - height / 2
                            width: 18
                            height: 18
                            radius: 3
                            color: typeCheck.checked ? MichiTheme.colors.accent : "transparent"
                            border.color: typeCheck.checked ? MichiTheme.colors.accent : MichiTheme.colors.borderCard
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "\u2713"
                                color: MichiTheme.colors.textOnAccent
                                font.pixelSize: 11
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
            text: "Rango de año"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            SearchField {
                id: yearFromField
                width: parent.width * 0.45
                placeholderText: "Desde"
                objectName: "filterYearFrom"
                Accessible.name: "Año desde"
                text: root._yearFrom > 0 ? String(root._yearFrom) : ""
                onTextChangedByUser: root._yearFrom = parseInt(text) || 0
            }

            Text {
                text: "\u2013"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.verticalCenter: parent.verticalCenter
            }

            SearchField {
                id: yearToField
                width: parent.width * 0.45
                placeholderText: "Hasta"
                objectName: "filterYearTo"
                Accessible.name: "Año hasta"
                text: root._yearTo > 0 ? String(root._yearTo) : ""
                onTextChangedByUser: root._yearTo = parseInt(text) || 0
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: MichiTheme.colors.borderSubtle
        }

        Text {
            text: "Calidad"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            Repeater {
                model: [
                    {key: "any", label: "Cualquiera"},
                    {key: "low", label: "Baja"},
                    {key: "standard", label: "Estándar"},
                    {key: "high", label: "Alta"},
                    {key: "lossless", label: "Lossless"},
                ]

                MichiButton {
                    text: modelData.label
                    variant: root._qualityFilter === modelData.key ? "primary" : "ghost"
                    implicitHeight: 28
                    objectName: "filterQuality_" + modelData.key
                    Accessible.name: "Calidad " + modelData.label + (root._qualityFilter === modelData.key ? " (activo)" : "")
                    onClicked: root._qualityFilter = modelData.key
                }
            }
        }

        Item { width: 1; height: MichiTheme.spacing.md }

        Row {
            width: parent.width
            spacing: MichiTheme.spacing.sm

            MichiButton {
                text: "Aplicar filtros"
                variant: "primary"
                objectName: "applyFiltersBtn"
                Accessible.name: "Aplicar filtros"
                onClicked: {
                    root.filtersApplied(root._typeFilters, root._yearFrom, root._yearTo, root._qualityFilter)
                    root.close()
                }
            }

            MichiButton {
                text: "Restablecer"
                variant: "ghost"
                objectName: "resetFiltersBtn"
                Accessible.name: "Restablecer filtros"
                onClicked: {
                    root._typeFilters = {
                        "track": true, "album": true, "artist": true,
                        "playlist": true, "folder": true, "genre": true,
                        "radio": true, "device": false, "server": false,
                        "action": false, "setting": false
                    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    root._yearFrom = 0
                    root._yearTo = 0
                    root._qualityFilter = "any"
                    yearFromField.text = ""
                    yearToField.text = ""
                    root.filtersReset()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                }
            }
        }
    }
}
