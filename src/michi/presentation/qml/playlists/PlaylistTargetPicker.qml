import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

MichiDialog {
    id: root

    property var playlistRows: []
    property var pinnedRows: []
    property var recentRows: []
    property var selectionPayload: ({ kind: "tracks", trackIds: [] })
    property string selectionDescription: ""
    property string query: ""
    readonly property var targetRows: root.buildTargetRows()
    signal targetRequested(string playlistId, string playlistName, var payload)
    signal newPlaylistRequested(var payload)

    title: qsTr("Add to playlist")
    width: 460
    height: 560
    standardButtons: Dialog.Cancel

    function matches(row) {
        return query.trim().length === 0
            || row.name.toLocaleLowerCase().indexOf(query.trim().toLocaleLowerCase()) !== -1
    }

    function appendSection(output, section, rows, excluded) {
        for (var index = 0; index < rows.length; ++index) {
            var row = rows[index]
            if (!row || excluded[row.playlistId] || !matches(row))
                continue
            output.push({ section: section, playlistId: row.playlistId,
                name: row.name, trackCount: row.trackCount })
            excluded[row.playlistId] = true
        }
    }

    function buildTargetRows() {
        var output = []
        var excluded = ({})
        appendSection(output, qsTr("Pinned"), pinnedRows || [], excluded)
        appendSection(output, qsTr("Recent"), recentRows || [], excluded)
        appendSection(output, qsTr("All playlists"), playlistRows || [], excluded)
        return output
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiText {
            Layout.fillWidth: true
            text: root.selectionDescription
            role: "secondary"
            wrapMode: Text.Wrap
        }

        MichiSearchField {
            Layout.fillWidth: true
            placeholderText: qsTr("Search playlists…")
            text: root.query
            onEdited: value => root.query = value
            onClearRequested: root.query = ""
        }

        ListView {
            id: targetList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.targetRows
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            section.property: "section"
            section.criteria: ViewSection.FullString
            section.delegate: MichiText {
                required property string section
                width: ListView.view.width
                height: MichiMetrics.controlSmall
                text: section
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                verticalAlignment: Text.AlignVCenter
            }
            ScrollBar.vertical: MichiScrollBar { }

            delegate: MichiEntityRow {
                required property var modelData
                width: ListView.view.width
                iconName: "playlist"
                title: modelData.name
                subtitle: qsTr("%1 tracks").arg(modelData.trackCount)
                onActivated: {
                    root.targetRequested(modelData.playlistId,
                        modelData.name, root.selectionPayload)
                    root.close()
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.targetRows.length === 0
            title: root.query.length > 0
                ? qsTr("No matching playlists") : qsTr("No playlists yet")
            message: qsTr("Create a playlist for this selection.")
            iconName: "playlist"
        }

        MichiButton {
            Layout.fillWidth: true
            text: qsTr("New playlist…")
            iconName: "plus"
            variant: "secondary"
            onClicked: {
                root.newPlaylistRequested(root.selectionPayload)
                root.close()
            }
        }
    }

    onOpenedChanged: if (opened) query = ""
}
