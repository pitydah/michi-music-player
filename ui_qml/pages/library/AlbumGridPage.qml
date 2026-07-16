import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    objectName: "albumGridPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Álbumes"

    property var albumModel: null
    property var bridge: null

    signal albumClicked(string albumKey, string title, string artist, int year)

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 32
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                LibraryViewSelector {
                    id: viewSelector
                    currentView: 0
                    onViewChanged: function(idx) { albumContainer.currentView = idx }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: root.albumModel ? root.albumModel.totalCount + " álbumes" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: root.albumModel && root.albumModel.totalCount > 0
                }
            }
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            AlbumGridView {
                id: albumGridView
                anchors.fill: parent
                visible: viewSelector.currentView === 0
                albumModel: root.albumModel
                bridge: root.bridge
                onAlbumClicked: function(key, title, artist, year) { root.albumClicked(key, title, artist, year) }
            }

            AlbumListView {
                id: albumListView
                anchors.fill: parent
                visible: viewSelector.currentView === 1
                albumModel: root.albumModel
                bridge: root.bridge
                onAlbumClicked: function(key, title, artist, year) { root.albumClicked(key, title, artist, year) }
            }
        }
    }
}
