import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

MichiDialog {
    id: root

    property var trackRows: []
    property var selectedTrackIds: []
    property string query: ""
    readonly property var filteredRows: (trackRows || []).filter(function(row) {
        var needle = root.query.trim().toLocaleLowerCase()
        if (needle.length === 0)
            return true
        return [row.title, row.artist, row.album, row.formatLabel]
            .join(" ").toLocaleLowerCase().indexOf(needle) !== -1
    })
    signal tracksRequested(var trackIds)

    title: qsTr("Add music")
    width: 920
    height: 620
    standardButtons: Dialog.Cancel

    function toggleTrack(trackId) {
        var next = selectedTrackIds.slice()
        var index = next.indexOf(trackId)
        if (index === -1)
            next.push(trackId)
        else
            next.splice(index, 1)
        selectedTrackIds = next
    }

    function begin() {
        selectedTrackIds = []
        query = ""
        open()
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiSearchField {
            Layout.fillWidth: true
            placeholderText: qsTr("Search title, artist, album or format…")
            text: root.query
            onEdited: value => root.query = value
            onClearRequested: root.query = ""
        }

        MichiTrackTable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            rows: root.filteredRows
            selectionEnabled: true
            selectedTrackIds: root.selectedTrackIds
            showArtwork: false
            showActions: false
            canFavorite: false
            canQueue: false
            canAddToPlaylist: false
            canInspect: false
            canNavigateEntities: false
            emptyTitle: qsTr("No matching tracks")
            onSelectionToggleRequested: trackId => root.toggleTrack(trackId)
        }

        RowLayout {
            Layout.fillWidth: true
            MichiText {
                Layout.fillWidth: true
                text: qsTr("%1 selected").arg(root.selectedTrackIds.length)
                role: "secondary"
            }
            MichiButton {
                text: qsTr("Add selected")
                enabled: root.selectedTrackIds.length > 0
                onClicked: {
                    root.tracksRequested(root.selectedTrackIds)
                    root.close()
                }
            }
        }
    }
}
