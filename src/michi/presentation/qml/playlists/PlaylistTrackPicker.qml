import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// PL-FINAL-13 + PL-10-FINAL-02: Playlist Add Tracks picker: real workflow,
// stays in the playlist context. The catalog is the CANONICAL playlist
// projection (playlists.addTrackCandidateRows over LibraryService.state
// .tracks) — NEVER LibraryBridge.songRows, which is filtered by the global
// Library search UI. Local search, multi-select, Select All visible
// (UNION), existing playlist tracks visibly marked and not addable,
// keyboard accessible, Esc closes, batch add (ONE persist).
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
    // PL-FINAL-A11: membership map O(1) — construido UNA vez por estado;
    // nunca indexOf() repetido dentro de delegates con bibliotecas grandes.
    property var presentMap: ({})

    signal addCompleted(int added, int alreadyPresent)

    // PL-FINAL-A09: UNA sola entrada de toggle — mouse, checkbox, Space,
    // Enter y Return comparten EXACTAMENTE la misma regla: un track ya
    // presente NO es addable y jamás entra a selectedPaths.
    function toggleIfAddable(path) {
        if (root.presentMap[path])
            return false
        var i = root.selectedPaths.indexOf(path)
        if (i === -1)
            root.selectedPaths = root.selectedPaths.concat([path])
        else {
            var copy = root.selectedPaths.slice()
            copy.splice(i, 1)
            root.selectedPaths = copy
        }
        return true
    }

    function _matches(row) {
        var q = root.query.trim().toLowerCase()
        if (q === "")
            return true
        return (row.title + " " + row.artist + " " + row.album)
            .toLowerCase().indexOf(q) !== -1
    }

    function _refresh() {
        var all = (typeof playlists !== "undefined" && playlists)
            ? playlists.addTrackCandidateRows : []
        var out = []
        for (var i = 0; i < all.length; ++i) {
            if (root._matches(all[i]))
                out.push(all[i])
        }
        root.visibleRows = out
        // PL-10-FINAL-15: si el CATÁLOGO cambió mientras el diálogo está
        // abierto, los paths que desaparecieron se podan de la selección
        // (nunca selecciones fantasma); los que siguen, se mantienen.
        root._pruneSelection(all)
    }

    function _pruneSelection(all) {
        var catalog = {}
        for (var i = 0; i < all.length; ++i)
            catalog[all[i].path] = true
        var kept = []
        for (var j = 0; j < root.selectedPaths.length; ++j) {
            if (catalog[root.selectedPaths[j]])
                kept.push(root.selectedPaths[j])
        }
        if (kept.length !== root.selectedPaths.length)
            root.selectedPaths = kept
    }

    function _rebuildPresentMap() {
        var map = {}
        for (var i = 0; i < root.presentPaths.length; ++i)
            map[root.presentPaths[i]] = true
        root.presentMap = map
    }

    function _isSelected(path) {
        return root.selectedPaths.indexOf(path) !== -1
    }

    function selectAllVisible() {
        // PL-FINAL-A10: UNION — la selección existente NUNCA se destruye;
        // solo se agregan los tracks visibles actuales addable (dedupe).
        var sel = root.selectedPaths.slice()
        for (var i = 0; i < root.visibleRows.length; ++i) {
            var path = root.visibleRows[i].path
            if (!root.presentMap[path] && sel.indexOf(path) === -1)
                sel.push(path)
        }
        root.selectedPaths = sel
    }

    function clearSelection() {
        root.selectedPaths = []
    }

    function _newSelectionCount() {
        var count = 0
        for (var i = 0; i < root.selectedPaths.length; ++i) {
            if (!root.presentMap[root.selectedPaths[i]])
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
        root._rebuildPresentMap()
        root._refresh()
        searchField.forceActiveFocus()
    }
    onPresentPathsChanged: root._rebuildPresentMap()

    Connections {
        target: typeof library !== "undefined" ? library : null
        function onLibrary_changed() { root._refresh() }
    }
    Connections {
        // PL-10-FINAL-02: el picker solo reacciona al CATÁLOGO CANÓNICO —
        // la búsqueda global de Library no lo afecta.
        target: typeof playlists !== "undefined" ? playlists : null
        function onTrackCatalogChanged() { root._refresh() }
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
                        root.presentMap[modelData.path] === true
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
                            onToggled: root.toggleIfAddable(modelData.path)
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
                        // PL-FINAL-A09: misma regla que checkbox/keys.
                        root.toggleIfAddable(modelData.path)
                    }
                    Keys.onReturnPressed: root.toggleIfAddable(modelData.path)
                    Keys.onEnterPressed: root.toggleIfAddable(modelData.path)
                    Keys.onSpacePressed: {
                        if (!pickItem.alreadyPresent)
                            root.toggleIfAddable(modelData.path)
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
