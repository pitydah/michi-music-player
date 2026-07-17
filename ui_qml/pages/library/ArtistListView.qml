import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Artist List View"
    objectName: "artistListView"
    focus: true
    id: root

    property var artistModel: null
    property var bridge: null

    signal artistClicked(string name)

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: "Lista de artistas"

        activeFocusOnTab: true

        focusPolicy: Qt.StrongFocus
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        model: root.artistModel
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        spacing: MichiTheme.spacing.xs

        ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

        delegate: MichiArtistRow {
            width: parent.width
            name: model.name || ""
            albumCount: model.albumCount || 0
            trackCount: model.trackCount || 0

            onClicked: root.artistClicked(model.name || "")
        }
    }
}
