import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// PL-FINAL-13 — Playlist Add Tracks picker: real workflow, stays in the
// playlist context. Reuses the CANONICAL library track projection
// (library.songRows) — no second scanner, no independent metadata source.
// Multi-select, search, Select All (visible filtered), existing playlist
// tracks visibly marked and not addable, keyboard accessible, Esc closes,
// Add disabled with zero new selections, batch add (ONE persist) via
// playlists.add_tracks.
MichiDialog {
    id: root

    objectName: "playlistTrackPicker"
    title: qsTr("Add tracks")
    standardButtons: Dialog.NoButton
    width: Math.min(720, parent ? parent.width - MichiSpacing.xl * 2 : 720)
    height: Math.min(600, parent ? parent.height - MichiSpacing.xl * 2 : 600)

    property string playlistId: ""
    property var presentPaths: []   // paths ya en la playlist (no addable)
    property var selectedPaths: []  // paths nuevos seleccionados
    property string query: ""
    property var visibleRows: []

    signal addCompleted(int added, int alreadyPresent)

    function _matches(row) {
        var q = root.query.trim().toLowerCase()
        if (q === "")
            return true
        return (row.title + " " + row.artist + " " + row.album)
            .toLowerCase().indexOf(q) !== -1
    }

    function _refresh() {
        var all = (typeof library !== "undefined" && library) ? library.songRows : []
        var out = []
        for (var i = 0; i < all.length; ++i) {
            if (root._matches(all[i]))
                out.push(all[i])
        }
        root.visibleRows = out
    }

    function _isSelected(path) {
        return root.selectedPaths.indexOf(path) !== -1
    }

    function _toggle(path) {
        var i = root.selectedPaths.indexOf(path)
        if (i === -1)
            root.selectedPaths = root.selectedPaths.concat([path])
        else {
            var copy = root.selectedPaths.slice()
            copy.splice(i, 1)
            root.selectedPaths = copy
        }
    }

    function selectAllVisible() {
        var sel = []
        for (var i = 0; i < root.visibleRows.length; ++i) {
            var row = root.visibleRows[i]
            if (root.presentPaths.indexOf(row.path) === -1)
                sel.push(row.path)
        }
        root.selectedPaths = sel
    }

    function clearSelection() {
        root.selectedPaths = []
    }

    function _newSelectionCount() {
        var count = 0
        for (var i = 0; i < root.selectedPaths.length; ++i) {
            if (root.presentPaths.indexOf(root.selectedPaths[i]) === -1)
                ++count
        }
        return count
    }

    function _add() {
        if (root._newSelectionCount() === 0)
            return
        var result = playlists.add_tracks(root.playlistId, root.selectedPaths)
        if (result.status === "updated") {
            root.addCompleted(result.addedCount, result.alreadyPresentCount)
            root.selectedPaths = []
            root.close()
        }
        // "persistence_failed": el connector informa exactamente una vez.
        // "no_change": nada nuevo que añadir (no cierra con falso éxito).
    }

    onOpened: {
        root.query = ""
        root.selectedPaths = []
        root._refresh()
        searchField.forceActiveFocus()
    }

    Connections {
        target: typeof library !== "undefined" ? library : null
        function onLibrary_changed() { root._refresh() }
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiTextField {
            id: searchField
            objectName: "playlistTrackPickerSearch"
            Layout.fillWidth: true
            placeholderText: qsTr("Search artist, title or album")
            text: root.query
            onTextChanged: {
                root.query = text
                root._refresh()
            }
            Accessible.name: qsTr("Search tracks to add")
        }

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                text: qsTr("%1 tracks available").arg(root.visibleRows.length)
                role: "caption"
                color: MichiPalette.textSecondary
            }
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("Select all visible")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlSmall
                enabled: root.visibleRows.length > 0
                accessibleName: qsTr("Select every filtered track")
                onClicked: root.selectAllVisible()
            }
            MichiButton {
                text: qsTr("Clear")
                variant: "ghost"
                implicitHeight: MichiMetrics.controlSmall
                enabled: root.selectedPaths.length > 0
                accessibleName: qsTr("Clear selection")
                onClicked: root.clearSelection()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ListView {
                id: pickerList
                anchors.fill: parent
                model: root.visibleRows
                clip: true
                spacing: 0
                reuseItems: true
                keyNavigationEnabled: true
                activeFocusOnTab: true
                ScrollBar.vertical: MichiScrollBar { }
                Accessible.role: Accessible.List
                Accessible.name: qsTr("Library tracks")

                delegate: ItemDelegate {
                    id: pickItem
                    required property int index
                    required property var modelData
                    width: pickerList.width
                    height: 46
                    hoverEnabled: true
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.title + " — " + modelData.artist

                    readonly property bool alreadyPresent:
                        root.presentPaths.indexOf(modelData.path) !== -1
                    readonly property bool isChecked: root._isSelected(modelData.path)

                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: MichiSpacing.sm
                        anchors.rightMargin: MichiSpacing.sm
                        spacing: MichiSpacing.md

                        CheckBox {
                            checked: pickItem.isChecked
                            enabled: !pickItem.alreadyPresent
                            Accessible.name: qsTr("Select ") + modelData.title
                            onToggled: root._toggle(modelData.path)
                        }

                        Artwork {
                            Layout.preferredWidth: 32
                            Layout.preferredHeight: 32
                            sourcePath: modelData.artworkPath || ""
                            fallbackText: modelData.title || "T"
                            radius: 4
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Layout.alignment: Qt.AlignVCenter
                            MichiText {
                                Layout.fillWidth: true
                                text: modelData.title
                                role: "body"
                                font.weight: Font.Medium
                                color: pickItem.alreadyPresent
                                    ? MichiPalette.textMuted : MichiPalette.textPrimary
                                elide: Text.ElideRight
                            }
                            MichiText {
                                Layout.fillWidth: true
                                visible: modelData.artist !== "" || modelData.album !== ""
                                text: [modelData.artist, modelData.album]
                                    .filter(v => v !== "").join(" · ")
                                role: "secondary"
                                color: MichiPalette.textSecondary
                                opacity: 0.65
                                elide: Text.ElideRight
                            }
                        }

                        MichiText {
                            visible: pickItem.alreadyPresent
                            text: qsTr("In playlist")
                            role: "caption"
                            color: MichiPalette.textSecondary
                            opacity: 0.7
                        }
                    }

                    background: Rectangle {
                        radius: 5
                        color: pickItem.hovered || pickItem.visualFocus
                            ? MichiSemanticColors.rowHover : "transparent"
                    }

                    onClicked: {
                        if (!pickItem.alreadyPresent)
                            root._toggle(modelData.path)
                    }
                    Keys.onReturnPressed: root._toggle(modelData.path)
                    Keys.onEnterPressed: root._toggle(modelData.path)
                    Keys.onSpacePressed: {
                        if (!pickItem.alreadyPresent)
                            root._toggle(modelData.path)
                    }
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                visible: root.visibleRows.length === 0
                spacing: MichiSpacing.sm
                MichiIcon {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                    name: "search"
                    iconColor: MichiPalette.textMuted
                }
                MichiText {
                    text: root.query.length > 0
                        ? qsTr("No tracks match your search")
                        : qsTr("Your library is empty")
                    role: "secondary"
                    color: MichiPalette.textSecondary
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                visible: root.selectedPaths.length > 0
                text: qsTr("%n selected", "", root._newSelectionCount())
                role: "technical"
                color: MichiPalette.textSecondary
            }
            Item { Layout.fillWidth: true }
            MichiButton {
                text: qsTr("Cancel")
                variant: "ghost"
                accessibleName: qsTr("Cancel — nothing is added")
                onClicked: root.close()
            }
            MichiButton {
                text: qsTr("Add %n track(s)", "", root._newSelectionCount())
                variant: "primary"
                enabled: root._newSelectionCount() > 0
                accessibleName: qsTr("Add selected tracks to playlist")
                onClicked: root._add()
            }
        }
    }
}
