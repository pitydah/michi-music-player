import QtQuick
import QtQuick.Controls.Basic
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

    elevation: "subtle"
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
                onClicked: clearQueueDialog.open()
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
            keyNavigationEnabled: true
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            Accessible.role: Accessible.List
            Accessible.name: "Queue tracks"
            ScrollBar.vertical: MichiScrollBar { }

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
                    selected: queueList.isCurrentItem
                    showRemove: true
                    showArtistColumn: root.width >= 460
                    showAlbumColumn: false
                    showQualityColumn: false
                    showDurationColumn: root.width >= 390
                    onActiveFocusChanged: {
                        if (activeFocus)
                            queueList.currentIndex = index
                    }
                    onActivated: root.trackClicked(index)
                    onRemoveRequested: root.removeRequested(index)
                }
                // Reorder affordances reveal on row hover, matching the
                // row's own hover-reveal trash (TrackRow opacity pattern).
                MichiIconButton {
                    iconName: "up"
                    accessibleName: "Move track up"
                    enabled: index > 0
                    opacity: queueRow.hovered || queueList.isCurrentItem ? 1 : 0.18
                    onClicked: root.moveRequested(index, index - 1)
                }
                MichiIconButton {
                    iconName: "down"
                    accessibleName: "Move track down"
                    enabled: index + 1 < root.count
                    opacity: queueRow.hovered || queueList.isCurrentItem ? 1 : 0.18
                    onClicked: root.moveRequested(index, index + 1)
                }
                HoverHandler { id: queueRow }
            }
        }
    }

    // Destructive action guard: clearing the queue requires confirmation.
    MichiDialog {
        id: clearQueueDialog
        title: qsTr("Clear queue?")
        modal: true
        contentItem: ColumnLayout {
            spacing: MichiSpacing.md
            MichiText {
                Layout.fillWidth: true
                Layout.preferredWidth: 320
                text: qsTr("Remove all %n track(s) from the queue?", "", root.count)
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: MichiSpacing.sm
                MichiButton {
                    text: qsTr("Cancel")
                    variant: "ghost"
                    onClicked: clearQueueDialog.close()
                }
                MichiButton {
                    text: qsTr("Clear queue")
                    variant: "danger"
                    onClicked: {
                        clearQueueDialog.close()
                        root.clearClicked()
                    }
                }
            }
        }
    }
}
