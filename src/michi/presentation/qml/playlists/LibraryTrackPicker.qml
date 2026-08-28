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
    signal tracksRequested(var trackIds)

    title: qsTr("Add music")
    width: 640
    height: 560
    standardButtons: Dialog.Cancel

    function isSelected(trackId) {
        return selectedTrackIds.indexOf(trackId) !== -1
    }

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
        open()
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.trackRows
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: MichiScrollBar { }

            delegate: MichiEntityRow {
                required property var modelData
                width: ListView.view.width
                iconName: "track"
                title: modelData.title
                subtitle: [modelData.artist, modelData.album]
                    .filter(value => value.length > 0).join(" · ")
                technical: modelData.formatLabel
                selected: root.isSelected(modelData.trackId)
                onActivated: root.toggleTrack(modelData.trackId)
            }
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
