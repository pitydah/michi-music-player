import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "artistGridPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Artistas")
    Accessible.description: qsTr("Cuadrícula adaptable de artistas de la biblioteca")

    property var artistModel: null
    property var bridge: null
    property int minimumCardWidth: width < 760 ? 158 : 184
    property bool automaticPagination: true

    signal artistClicked(string name)

    function openCurrentArtist() {
        if (!root.artistModel || gridView.currentIndex < 0 || !root.artistModel.get)
            return
        var artist = root.artistModel.get(gridView.currentIndex)
        var name = artist.name || ""
        if (name)
            root.artistClicked(name)
    }

    function maybeFetchMore() {
        if (!root.automaticPagination || !root.artistModel || !root.artistModel.hasMore ||
                root.artistModel.loadingMore || gridView.moving)
            return
        var remaining = gridView.contentHeight - (gridView.contentY + gridView.height)
        if (remaining <= gridView.cellHeight * 2)
            root.artistModel.fetchMore()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceToolbar
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.artistModel
                          ? qsTr("%1 artistas").arg(root.artistModel.totalCount)
                          : qsTr("Artistas")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    visible: root.width >= 760
                    text: qsTr("Enter abre el artista seleccionado")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                }

                Item { Layout.fillWidth: true }

                BusyIndicator {
                    Layout.preferredWidth: 20
                    Layout.preferredHeight: 20
                    visible: root.artistModel && root.artistModel.loadingMore
                    running: visible
                    Accessible.name: qsTr("Cargando más artistas")
                }
            }
        }

        GridView {
            id: gridView
            objectName: "artistGrid"
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.artistModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            cacheBuffer: cellHeight * 2

            readonly property int columnCount: Math.max(
                1,
                Math.floor(width / root.minimumCardWidth)
            )
            cellWidth: width / columnCount
            cellHeight: Math.max(206, Math.min(258, cellWidth + 42))

            onContentYChanged: paginationTimer.restart()
            onMovementEnded: root.maybeFetchMore()
            onCurrentIndexChanged: {
                if (currentIndex >= 0) {
                    positionViewAtIndex(currentIndex, GridView.Contain)
                    if (root.artistModel && root.artistModel.hasMore &&
                            !root.artistModel.loadingMore &&
                            currentIndex >= Math.max(0, count - 5))
                        root.artistModel.fetchMore()
                }
            }

            Keys.onReturnPressed: root.openCurrentArtist()
            Keys.onEnterPressed: root.openCurrentArtist()
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Home) {
                    currentIndex = count > 0 ? 0 : -1
                    positionViewAtBeginning()
                    event.accepted = true
                } else if (event.key === Qt.Key_End) {
                    currentIndex = count > 0 ? count - 1 : -1
                    positionViewAtEnd()
                    root.maybeFetchMore()
                    event.accepted = true
                }
            }

            Timer {
                id: paginationTimer
                interval: 90
                repeat: false
                onTriggered: root.maybeFetchMore()
            }

            ScrollBar.vertical: ScrollBar {
                width: 8
                policy: ScrollBar.AsNeeded
            }

            delegate: Item {
                id: artistDelegate
                required property int index
                required property string name
                required property var trackCount
                required property var albumCount
                required property string coverKey

                width: gridView.cellWidth
                height: gridView.cellHeight

                ArtistCard {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    artistName: artistDelegate.name
                    trackCount: Number(artistDelegate.trackCount) || 0
                    albumCount: Number(artistDelegate.albumCount) || 0
                    coverKey: artistDelegate.coverKey
                    selected: GridView.isCurrentItem

                    onClicked: {
                        gridView.currentIndex = artistDelegate.index
                        root.artistClicked(artistDelegate.name)
                    }
                }
            }

            footer: Item {
                width: gridView.width
                height: root.artistModel && root.artistModel.hasMore
                        ? 52
                        : MichiTheme.spacing.md

                MichiButton {
                    anchors.centerIn: parent
                    visible: root.artistModel && root.artistModel.hasMore
                    enabled: root.artistModel && !root.artistModel.loadingMore
                    text: root.artistModel && root.artistModel.loadingMore
                          ? qsTr("Cargando…")
                          : qsTr("Cargar más artistas")
                    variant: "ghost"
                    onClicked: root.artistModel.fetchMore()
                }
            }
        }
    }
}
