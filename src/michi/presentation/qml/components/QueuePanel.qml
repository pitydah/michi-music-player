import QtQuick
import QtQuick.Layouts
import "../controls"
import "../media"
import "../patterns"
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root

    property var trackRows: []
    property int currentIndex: -1
    property int count: 0
    property bool hasPrev: false
    property bool hasNext: false
    property string repeatMode: "NONE"
    property bool shuffleEnabled: false

    signal trackClicked(int index)
    signal moveRequested(int fromIndex, int toIndex)
    signal removeRequested(int index)
    signal clearClicked()
    signal previousRequested()
    signal nextRequested()
    signal repeatModeRequested(string mode)
    signal shuffleRequested(bool enabled)
    signal closeRequested()

    elevation: "elevated"
    accented: true
    accentColor: MichiPalette.auroraPurple
    contentPadding: MichiSpacing.lg

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiSpacing.md

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            PageHeader {
                Layout.fillWidth: true
                title: "Queue"
                subtitle: root.count + (root.count === 1 ? " track" : " tracks")
            }
            MichiIconButton {
                iconName: "close"
                accessibleName: "Close queue"
                onClicked: root.closeRequested()
            }
            MichiButton {
                text: "Clear"
                variant: "ghost"
                enabled: root.count > 0
                onClicked: root.clearClicked()
            }
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.count === 0
            title: "Queue is empty"
            message: "Play a track from the library to start listening."
        }

        ListView {
            id: queueList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.count > 0
            model: root.trackRows
            clip: true
            spacing: MichiSpacing.xs
            boundsBehavior: Flickable.StopAtBounds

            delegate: RowLayout {
                required property int index
                required property var modelData
                width: queueList.width
                spacing: MichiSpacing.xs

                TrackRow {
                    Layout.fillWidth: true
                    numberText: String(index + 1)
                    title: modelData.title
                    artist: modelData.artist || ""
                    album: modelData.album || ""
                    durationMs: modelData.durationMs || 0
                    playing: index === root.currentIndex
                    selected: index === root.currentIndex
                    showRemove: true
                    showArtistColumn: root.width >= 460
                    showAlbumColumn: false
                    showQualityColumn: false
                    showDurationColumn: root.width >= 390
                    onActivated: root.trackClicked(index)
                    onRemoveRequested: root.removeRequested(index)
                }
                MichiIconButton {
                    iconName: "up"
                    accessibleName: "Move track up"
                    enabled: index > 0
                    onClicked: root.moveRequested(index, index - 1)
                }
                MichiIconButton {
                    iconName: "down"
                    accessibleName: "Move track down"
                    enabled: index + 1 < root.count
                    onClicked: root.moveRequested(index, index + 1)
                }
            }
        }
    }
}
