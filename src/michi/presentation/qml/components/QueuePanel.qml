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

    elevation: "elevated"
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
            MichiButton {
                text: "Clear"
                variant: "ghost"
                enabled: root.count > 0
                onClicked: root.clearClicked()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm

            MichiSegmentedControl {
                Layout.fillWidth: true
                model: [
                    { value: "NONE", label: "Repeat off" },
                    { value: "ONE", label: "Repeat one" },
                    { value: "ALL", label: "Repeat all" }
                ]
                currentValue: root.repeatMode
                compact: root.width < 430
                onSelected: mode => root.repeatModeRequested(mode)
            }
            MichiSwitch {
                text: "Shuffle"
                checked: root.shuffleEnabled
                onToggled: root.shuffleRequested(checked)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.sm
            MichiButton {
                Layout.fillWidth: true
                text: "Previous"
                variant: "secondary"
                enabled: root.hasPrev
                onClicked: root.previousRequested()
            }
            MichiButton {
                Layout.fillWidth: true
                text: "Next"
                variant: "secondary"
                enabled: root.hasNext
                onClicked: root.nextRequested()
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
                    playing: index === root.currentIndex
                    selected: index === root.currentIndex
                    onActivated: root.trackClicked(index)
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
                MichiIconButton {
                    iconName: "trash"
                    accessibleName: "Remove from queue"
                    onClicked: root.removeRequested(index)
                }
            }
        }
    }
}
