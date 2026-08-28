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
    property var trackIds: []
    property string selectionDescription: ""
    signal targetRequested(string playlistId, string playlistName, var trackIds)

    title: qsTr("Add to playlist")
    width: 440
    height: Math.min(520, 160 + (playlistRows || []).length
        * MichiThemeState.rowHeight)
    standardButtons: Dialog.Cancel

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        MichiText {
            Layout.fillWidth: true
            text: root.selectionDescription.length > 0
                ? root.selectionDescription
                : (root.trackIds || []).length === 1
                ? qsTr("Choose a playlist for this track.")
                : qsTr("Choose a playlist for %1 tracks.").arg(
                    (root.trackIds || []).length)
            role: "secondary"
            wrapMode: Text.Wrap
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.playlistRows
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: MichiScrollBar { }

            delegate: MichiEntityRow {
                required property var modelData
                width: ListView.view.width
                iconName: "playlist"
                title: modelData.name
                subtitle: qsTr("%1 tracks").arg(modelData.trackCount)
                onActivated: {
                    root.targetRequested(
                        modelData.playlistId, modelData.name, root.trackIds)
                    root.close()
                }
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: (root.playlistRows || []).length === 0
            title: qsTr("No playlists yet")
            message: qsTr("Create a playlist before adding tracks.")
            iconName: "playlist"
        }
    }
}
