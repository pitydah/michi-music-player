import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "libraryFilterBar"
    focus: true

    Accessible.role: Accessible.ToolBar
    Accessible.name: qsTr("Filtros de biblioteca")
    Accessible.description: qsTr("Filtros por formato, estado y metadatos")

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property bool expanded: false
    property string specialFilter: ""
    property string genreText: ""
    property string composerText: ""
    property string yearText: ""
    property string _appliedGenre: ""
    property string _appliedComposer: ""
    property string _appliedYear: ""

    readonly property string activeFormat: root.lib && root.lib.activeFormatFilter
                                                    ? root.lib.activeFormatFilter
                                                    : ""
    readonly property int activeFilterCount:
        (root.activeFormat !== "" ? 1 : 0) +
        (root.specialFilter !== "" ? 1 : 0) +
        (root.genreText !== "" ? 1 : 0) +
        (root.composerText !== "" ? 1 : 0) +
        (root.yearText !== "" ? 1 : 0)

    signal formatFilterChanged(string fmt)
    signal genreFilterChanged(string genre)
    signal composerFilterChanged(string composer)
    signal yearFilterChanged(string year)

    implicitHeight: root.expanded ? 92 : 46

    function clearAll() {
        var hadFormat = root.activeFormat !== ""
        var hadGenre = root.genreText !== "" || root._appliedGenre !== ""
        var hadComposer = root.composerText !== "" || root._appliedComposer !== ""
        var hadYear = root.yearText !== "" || root._appliedYear !== ""

        root.specialFilter = ""
        root.genreText = ""
        root.composerText = ""
        root.yearText = ""
        root._appliedGenre = ""
        root._appliedComposer = ""
        root._appliedYear = ""

        if (root.lib && root.lib.clearFilters) {
            root.lib.clearFilters()
            return
        }

        if (hadFormat) root.formatFilterChanged("")
        if (hadGenre) root.genreFilterChanged("")
        if (hadComposer) root.composerFilterChanged("")
        if (hadYear) root.yearFilterChanged("")
    }

    function applySpecial(name) {
        root.specialFilter = root.specialFilter === name ? "" : name
        if (!root.lib)
            return
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
        var genre = genreField.text.trim()
        var composer = composerField.text.trim()
        var year = yearField.text.trim()

        root.genreText = genre
        root.composerText = composer
        root.yearText = year

        if (genre !== root._appliedGenre) {
            root._appliedGenre = genre
            root.genreFilterChanged(genre)
        }
        if (composer !== root._appliedComposer) {
            root._appliedComposer = composer
            root.composerFilterChanged(composer)
        }
        if (year !== root._appliedYear) {
            root._appliedYear = year
            root.yearFilterChanged(year)
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.sm
            anchors.rightMargin: MichiTheme.spacing.sm
            anchors.topMargin: 4
            anchors.bottomMargin: 4
            spacing: 4

            Flickable {
                id: quickFilters
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                contentWidth: quickFilterRow.width
                contentHeight: height
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.HorizontalFlick

                ScrollBar.horizontal: ScrollBar {
                    policy: quickFilters.contentWidth > quickFilters.width
                            ? ScrollBar.AsNeeded
                            : ScrollBar.AlwaysOff
                    height: 4
                }

                Row {
                    id: quickFilterRow
                    height: parent.height
                    spacing: MichiTheme.spacing.xs

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Formato")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        font.capitalization: Font.AllUppercase
                    }

                    Repeater {
                        model: [
                            { label: qsTr("Todos"), value: "" },
                            { label: "FLAC", value: "flac" },
                            { label: "MP3", value: "mp3" },
                            { label: "AAC", value: "m4a" },
                            { label: "WAV", value: "wav" },
                            { label: "DSD", value: "dsd" }
                        ]

                        Rectangle {
                            required property var modelData
                            width: formatChipText.implicitWidth + MichiTheme.spacing.lg
                            height: 28
                            anchors.verticalCenter: parent.verticalCenter
                            radius: MichiTheme.radius.pill
                            readonly property bool selected: root.activeFormat === modelData.value
                            color: selected
                                   ? MichiTheme.colors.accentSelection
                                   : formatChipMouse.containsMouse
                                     ? MichiTheme.colors.surfaceHover
                                     : MichiTheme.colors.surfaceInput
                            border.width: MichiTheme.borderWidth
                            border.color: selected
                                          ? MichiTheme.colors.borderActive
                                          : MichiTheme.colors.borderSubtle

                            Accessible.role: Accessible.Button
                            Accessible.name: qsTr("Filtrar por %1").arg(modelData.label)
                            Accessible.checked: selected
                            Accessible.onPressAction: formatChipMouse.clicked(null)

                            Text {
                                id: formatChipText
                                anchors.centerIn: parent
                                text: modelData.label
                                color: parent.selected
                                       ? MichiTheme.colors.accentBlue
                                       : MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }

                            MouseArea {
                                id: formatChipMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.specialFilter = ""
                                    root.formatFilterChanged(modelData.value)
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: 1
                        height: 22
                        anchors.verticalCenter: parent.verticalCenter
                        color: MichiTheme.colors.borderSubtle
                    }

                    Repeater {
                        model: [
                            { label: qsTr("Favoritos"), value: "favorites" },
                            { label: qsTr("No reproducidos"), value: "unplayed" },
                            { label: qsTr("Ausentes"), value: "missing" }
                        ]

                        Rectangle {
                            required property var modelData
                            width: specialChipText.implicitWidth + MichiTheme.spacing.lg
                            height: 28
                            anchors.verticalCenter: parent.verticalCenter
                            radius: MichiTheme.radius.pill
                            readonly property bool selected: root.specialFilter === modelData.value
                            color: selected
                                   ? MichiTheme.colors.accentSelection
                                   : specialChipMouse.containsMouse
                                     ? MichiTheme.colors.surfaceHover
                                     : "transparent"
                            border.width: MichiTheme.borderWidth
                            border.color: selected
                                          ? MichiTheme.colors.borderActive
                                          : MichiTheme.colors.borderSubtle

                            Accessible.role: Accessible.Button
                            Accessible.name: modelData.label
                            Accessible.checked: selected

                            Text {
                                id: specialChipText
                                anchors.centerIn: parent
                                text: modelData.label
                                color: parent.selected
                                       ? MichiTheme.colors.accentBlue
                                       : MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.captionSize
                                font.weight: MichiTheme.typography.weightSemiBold
                            }

                            MouseArea {
                                id: specialChipMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.applySpecial(modelData.value)
                            }
                        }
                    }

                    MichiButton {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.expanded ? qsTr("Ocultar avanzados") : qsTr("Filtros avanzados")
                        variant: "ghost"
                        onClicked: root.expanded = !root.expanded
                    }

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: activeCountText.implicitWidth + MichiTheme.spacing.md
                        height: 26
                        radius: MichiTheme.radius.pill
                        color: MichiTheme.colors.surfaceInput
                        border.width: MichiTheme.borderWidth
                        border.color: MichiTheme.colors.borderSubtle
                        visible: root.activeFilterCount > 0

                        Text {
                            id: activeCountText
                            anchors.centerIn: parent
                            text: qsTr("%1 activos").arg(root.activeFilterCount)
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                    }

                    MichiButton {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Limpiar todo")
                        variant: "ghost"
                        visible: root.activeFilterCount > 0
                        onClicked: root.clearAll()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                visible: root.expanded
                spacing: MichiTheme.spacing.sm

                TextField {
                    id: genreField
                    Layout.fillWidth: true
                    Layout.preferredWidth: 150
                    Layout.fillHeight: true
                    placeholderText: qsTr("Género, por ejemplo Jazz")
                    text: root.genreText
                    color: MichiTheme.colors.textPrimary
                    placeholderTextColor: MichiTheme.colors.textMuted
                    selectByMouse: true
                    activeFocusOnTab: visible
                    Accessible.name: qsTr("Género")
                    background: Rectangle {
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceInput
                        border.width: genreField.activeFocus
                                      ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
                        border.color: genreField.activeFocus
                                      ? MichiTheme.colors.borderFocus
                                      : MichiTheme.colors.borderSubtle
                    }
                    onAccepted: root.applyAdvanced()
                }

                TextField {
                    id: composerField
                    Layout.fillWidth: true
                    Layout.preferredWidth: 150
                    Layout.fillHeight: true
                    placeholderText: qsTr("Compositor")
                    text: root.composerText
                    color: MichiTheme.colors.textPrimary
                    placeholderTextColor: MichiTheme.colors.textMuted
                    selectByMouse: true
                    activeFocusOnTab: visible
                    Accessible.name: qsTr("Compositor")
                    background: Rectangle {
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceInput
                        border.width: composerField.activeFocus
                                      ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
                        border.color: composerField.activeFocus
                                      ? MichiTheme.colors.borderFocus
                                      : MichiTheme.colors.borderSubtle
                    }
                    onAccepted: root.applyAdvanced()
                }

                TextField {
                    id: yearField
                    Layout.preferredWidth: 96
                    Layout.fillHeight: true
                    placeholderText: qsTr("Año")
                    text: root.yearText
                    color: MichiTheme.colors.textPrimary
                    placeholderTextColor: MichiTheme.colors.textMuted
                    inputMethodHints: Qt.ImhDigitsOnly
                    selectByMouse: true
                    activeFocusOnTab: visible
                    Accessible.name: qsTr("Año de publicación")
                    validator: IntValidator {
                        bottom: 1000
                        top: new Date().getFullYear() + 1
                    }
                    background: Rectangle {
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceInput
                        border.width: yearField.activeFocus
                                      ? MichiTheme.borderWidthFocus
                                      : MichiTheme.borderWidth
                        border.color: yearField.activeFocus
                                      ? MichiTheme.colors.borderFocus
                                      : MichiTheme.colors.borderSubtle
                    }
                    onAccepted: root.applyAdvanced()
                }

                MichiButton {
                    text: qsTr("Aplicar")
                    variant: "primary"
                    onClicked: root.applyAdvanced()
                }

                MichiButton {
                    text: qsTr("Limpiar")
                    variant: "ghost"
                    enabled: root.genreText !== "" || root.composerText !== "" || root.yearText !== ""
                    onClicked: {
                        root.genreText = ""
                        root.composerText = ""
                        root.yearText = ""
                        root.applyAdvanced()
                    }
                }
            }
        }
    }
}
