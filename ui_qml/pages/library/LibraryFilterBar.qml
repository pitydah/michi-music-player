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

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property bool expanded: false
    property string specialFilter: ""
    property string genreText: ""
    property string yearText: ""

    signal formatFilterChanged(string fmt)
    signal genreFilterChanged(string genre)
    signal yearFilterChanged(string year)

    implicitHeight: root.expanded ? 88 : 44

    function clearAll() {
        root.specialFilter = ""
        root.genreText = ""
        root.yearText = ""
        root.formatFilterChanged("")
        root.genreFilterChanged("")
        root.yearFilterChanged("")
    }

    function applySpecial(name) {
        root.specialFilter = root.specialFilter === name ? "" : name
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

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                spacing: MichiTheme.spacing.xs

                Text {
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
                        { label: "WAV", value: "wav" },
                        { label: "DSD", value: "dsd" }
                    ]

                    Rectangle {
                        required property var modelData
                        Layout.preferredWidth: chipText.implicitWidth + MichiTheme.spacing.lg
                        Layout.preferredHeight: 28
                        radius: MichiTheme.radius.pill
                        readonly property bool selected: root.specialFilter === "" &&
                                                         ((!root.lib && modelData.value === "") ||
                                                          (root.lib && root.lib.activeFormatFilter === modelData.value))
                        color: selected
                               ? MichiTheme.colors.accentSelection
                               : chipMouse.containsMouse
                                 ? MichiTheme.colors.surfaceHover
                                 : MichiTheme.colors.surfaceInput
                        border.width: MichiTheme.borderWidth
                        border.color: selected ? MichiTheme.colors.borderActive : MichiTheme.colors.borderSubtle

                        Text {
                            id: chipText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                        MouseArea {
                            id: chipMouse
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

                Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 22; color: MichiTheme.colors.borderSubtle }

                Repeater {
                    model: [
                        { label: qsTr("Favoritos"), value: "favorites" },
                        { label: qsTr("No reproducidos"), value: "unplayed" },
                        { label: qsTr("Ausentes"), value: "missing" }
                    ]
                    Rectangle {
                        required property var modelData
                        Layout.preferredWidth: specialText.implicitWidth + MichiTheme.spacing.lg
                        Layout.preferredHeight: 28
                        radius: MichiTheme.radius.pill
                        readonly property bool selected: root.specialFilter === modelData.value
                        color: selected
                               ? MichiTheme.colors.accentSelection
                               : specialMouse.containsMouse
                                 ? MichiTheme.colors.surfaceHover
                                 : "transparent"
                        border.width: MichiTheme.borderWidth
                        border.color: selected ? MichiTheme.colors.borderActive : MichiTheme.colors.borderSubtle

                        Text {
                            id: specialText
                            anchors.centerIn: parent
                            text: modelData.label
                            color: parent.selected ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }
                        MouseArea {
                            id: specialMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.applySpecial(modelData.value)
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: root.expanded ? qsTr("Ocultar") : qsTr("Avanzados")
                    variant: "ghost"
                    onClicked: root.expanded = !root.expanded
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                visible: root.expanded
                spacing: MichiTheme.spacing.sm

                TextField {
                    id: genreField
                    Layout.preferredWidth: 190
                    Layout.fillHeight: true
                    placeholderText: qsTr("Género, por ejemplo Jazz")
                    text: root.genreText
                    color: MichiTheme.colors.textPrimary
                    placeholderTextColor: MichiTheme.colors.textMuted
                    selectByMouse: true
                    background: Rectangle {
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceInput
                        border.width: genreField.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                        border.color: genreField.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                    }
                    onAccepted: {
                        root.genreText = text.trim()
                        root.genreFilterChanged(root.genreText)
                    }
                }

                TextField {
                    id: yearField
                    Layout.preferredWidth: 130
                    Layout.fillHeight: true
                    placeholderText: qsTr("Año")
                    text: root.yearText
                    color: MichiTheme.colors.textPrimary
                    placeholderTextColor: MichiTheme.colors.textMuted
                    inputMethodHints: Qt.ImhDigitsOnly
                    selectByMouse: true
                    background: Rectangle {
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceInput
                        border.width: yearField.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                        border.color: yearField.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                    }
                    onAccepted: {
                        root.yearText = text.trim()
                        root.yearFilterChanged(root.yearText)
                    }
                }

                MichiButton {
                    text: qsTr("Aplicar")
                    variant: "primary"
                    onClicked: {
                        root.genreText = genreField.text.trim()
                        root.yearText = yearField.text.trim()
                        root.genreFilterChanged(root.genreText)
                        root.yearFilterChanged(root.yearText)
                    }
                }
                MichiButton {
                    text: qsTr("Limpiar")
                    variant: "ghost"
                    onClicked: {
                        root.clearAll()
                        if (root.lib && root.lib.clearFilters) root.lib.clearFilters()
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
