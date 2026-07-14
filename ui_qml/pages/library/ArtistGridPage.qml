import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var artistModel: null
    property var bridge: null

    signal artistClicked(string name)

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 32
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                Text {
                    text: root.artistModel ? root.artistModel.totalCount + " artistas" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root.artistModel && root.artistModel.totalCount > 0
                }

                Item { Layout.fillWidth: true }
            }
        }

        GridView {
            id: gridView
            Layout.fillWidth: true; Layout.fillHeight: true
            anchors.margins: MichiTheme.spacing.md
            model: root.artistModel
            cellWidth: 160
            cellHeight: 180
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: ArtistCard {
                width: gridView.cellWidth - MichiTheme.spacing.md
                height: gridView.cellHeight - MichiTheme.spacing.md
                artistName: model.name || ""
                trackCount: model.trackCount || 0
                albumCount: model.albumCount || 0

                onClicked: root.artistClicked(model.name || "")
            }
        }
    }
}
