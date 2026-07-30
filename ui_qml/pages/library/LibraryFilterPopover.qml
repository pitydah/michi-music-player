import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "libraryFilterBar"
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Filtros de biblioteca")
    implicitHeight: 0

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property string specialFilter: ""
    property string genreText: ""
    property string composerText: ""
    property string yearText: ""
    property bool expanded: false
    property string _appliedGenre: ""
    property string _appliedComposer: ""
    property string _appliedYear: ""
    readonly property string activeFormat: root.lib && root.lib.activeFormatFilter
                                                   ? root.lib.activeFormatFilter : ""
    readonly property int activeFilterCount:
        (activeFormat !== "" ? 1 : 0) + (specialFilter !== "" ? 1 : 0) +
        (genreText !== "" ? 1 : 0) + (composerText !== "" ? 1 : 0) +
        (yearText !== "" ? 1 : 0)

    signal formatFilterChanged(string format)
    signal genreFilterChanged(string genre)
    signal composerFilterChanged(string composer)
    signal yearFilterChanged(string year)

    function open() { filterPopup.open() }
    function chooseFormat(value) {
        root.specialFilter = ""
        root.formatFilterChanged(value)
    }
    function applySpecial(value) {
        root.specialFilter = root.specialFilter === value ? "" : value
        if (!root.lib) return
        if (root.specialFilter === "favorites" && root.lib.setFavoritesFilter)
            root.lib.setFavoritesFilter()
        else if (root.specialFilter === "unplayed" && root.lib.setUnplayedFilter)
            root.lib.setUnplayedFilter()
        else if (root.specialFilter === "missing" && root.lib.setMissingFilter)
            root.lib.setMissingFilter()
        else if (root.specialFilter === "" && root.lib.clearSpecialFilters)
            root.lib.clearSpecialFilters()
    }
    function applyAdvanced() {
        root.genreText = genreField.text.trim()
        root.composerText = composerField.text.trim()
        root.yearText = yearField.text.trim()
        root._appliedGenre = root.genreText
        root._appliedComposer = root.composerText
        root._appliedYear = root.yearText
        root.genreFilterChanged(root.genreText)
        root.composerFilterChanged(root.composerText)
        root.yearFilterChanged(root.yearText)
    }
    function clearAll() {
        root.specialFilter = ""
        root.genreText = ""
        root.composerText = ""
        root.yearText = ""
        root._appliedGenre = ""
        root._appliedComposer = ""
        root._appliedYear = ""
        formatCombo.currentIndex = 0
        if (root.lib && root.lib.clearFilters) root.lib.clearFilters()
    }

    Popup {
        id: filterPopup
        objectName: "libraryFiltersPopup"
        parent: Overlay.overlay
        width: Math.min(420, parent ? parent.width - MichiTheme.spacing.xl * 2 : 420)
        height: advancedToggle.checked ? 410 : 238
        x: parent ? parent.width - width - MichiTheme.spacing.xl : 0
        y: MichiTheme.headerHeight + MichiTheme.spacing.sm
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: MichiTheme.spacing.lg

        background: Rectangle {
            radius: MichiTheme.radius.xl
            color: MichiTheme.colors.surfaceOverlay
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
        }

        contentItem: ColumnLayout {
            spacing: MichiTheme.spacing.md

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: qsTr("Filtrar biblioteca")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }
                Text {
                    visible: root.activeFilterCount > 0
                    text: qsTr("%1 activos").arg(root.activeFilterCount)
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }

            ComboBox {
                id: formatCombo
                Layout.fillWidth: true
                model: {
                    var lib = typeof libraryBridge !== "undefined" ? libraryBridge : null
                    var formats = lib ? lib.getFormats() : []
                    var result = [qsTr("Todos los formatos")]
                    for (var i = 0; i < formats.length; i++)
                        result.push(formats[i])
                    return result
                }
                currentIndex: {
                    var lib = typeof libraryBridge !== "undefined" ? libraryBridge : null
                    var formats = lib ? lib.getFormats() : []
                    var idx = formats.indexOf(root.activeFormat.toUpperCase())
                    return idx >= 0 ? idx + 1 : 0
                }
                onActivated: {
                    var lib = typeof libraryBridge !== "undefined" ? libraryBridge : null
                    var formats = lib ? lib.getFormats() : []
                    root.chooseFormat(currentIndex === 0 ? "" : (formats[currentIndex - 1] || ""))
                }
                Accessible.name: qsTr("Formato de audio")
            }

            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: [
                        { label: qsTr("Favoritos"), value: "favorites" },
                        { label: qsTr("No reproducidos"), value: "unplayed" },
                        { label: qsTr("Ausentes"), value: "missing" }
                    ]
                    MichiButton {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        variant: root.specialFilter === modelData.value ? "primary" : "secondary"
                        onClicked: root.applySpecial(modelData.value)
                    }
                }
            }

            CheckBox {
                id: advancedToggle
                text: qsTr("Filtros avanzados")
                checked: root.expanded
                onToggled: root.expanded = checked
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: advancedToggle.checked
                spacing: MichiTheme.spacing.sm
                TextField { id: genreField; Layout.fillWidth: true; placeholderText: qsTr("Género"); text: root.genreText }
                TextField { id: composerField; Layout.fillWidth: true; placeholderText: qsTr("Compositor"); text: root.composerText }
                TextField { id: yearField; Layout.fillWidth: true; placeholderText: qsTr("Año"); text: root.yearText }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                MichiButton {
                    text: qsTr("Limpiar")
                    variant: "ghost"
                    visible: root.activeFilterCount > 0
                    onClicked: root.clearAll()
                }
                MichiButton {
                    text: advancedToggle.checked ? qsTr("Aplicar") : qsTr("Listo")
                    variant: "primary"
                    onClicked: {
                        if (advancedToggle.checked) root.applyAdvanced()
                        filterPopup.close()
                    }
                }
            }
        }
    }
}
