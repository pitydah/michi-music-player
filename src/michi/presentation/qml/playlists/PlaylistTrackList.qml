import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

// PlaylistTrackList — quiet track rows with consistent music metadata.
// Rows come from the canonical bridge projection (no filesystem work in
// QML). Reorder: Move Up / Move Down via the row context menu (desktop
// reliable path for 1.0). Removing a track NEVER touches the file — the
// wording is "Remove from playlist".
Item {
    id: root

    property var rows: []
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

    implicitHeight: 420
    clip: true

    ListView {
        anchors.fill: parent
        clip: true
        model: root.rows
        delegate: ItemDelegate {
            id: trackItem
            width: ListView.view.width
            height: MichiMetrics.controlLarge + MichiSpacing.xs
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.ListItem
            Accessible.name: modelData.title + " — " + modelData.artist

            contentItem: RowLayout {
                spacing: MichiSpacing.md
                MichiText {
                    text: (index + 1)
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                    Layout.preferredWidth: 32
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    MichiText {
                        text: modelData.title
                        role: "secondary"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        color: MichiPalette.textPrimary
                    }
                    MichiText {
                        visible: modelData.artist !== ""
                        text: modelData.artist
                        role: "technical"
                        technical: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        color: MichiPalette.textSecondary
                    }
                }
                MichiText {
                    text: modelData.album
                    role: "technical"
                    technical: true
                    elide: Text.ElideRight
                    Layout.preferredWidth: Math.min(200, root.width * 0.22)
                    color: MichiPalette.textSecondary
                }
                MichiText {
                    text: modelData.durationMs > 0 ? formatTime(modelData.durationMs) : ""
                    role: "technical"
                    technical: true
                    color: MichiPalette.textMuted
                }
                MichiIconButton {
                    iconName: "more"
                    accessibleName: qsTr("More options for ") + modelData.title
                    onClicked: trackMenu.popup()
                }
            }

            Keys.onUpPressed: event => {
                if (event.modifiers & Qt.AltModifier) {
                    if (index > 0) {
                        root.moveTrackRequested(index, index - 1)
                        event.accepted = true
                    }
                }
            }
            Keys.onDownPressed: event => {
                if (event.modifiers & Qt.AltModifier) {
                    if (index < root.rows.length - 1) {
                        root.moveTrackRequested(index, index + 1)
                        event.accepted = true
                    }
                }
            }

            background: Rectangle {
                radius: MichiRadius.md
                color: trackItem.hovered || trackItem.visualFocus
                    ? MichiSemanticColors.surfaceHover : "transparent"
                Behavior on color {
                    enabled: !MichiAccessibility.reducedMotion
                    ColorAnimation { duration: MichiMotion.micro }
                }
                MichiFocusRing { visualFocus: trackItem.visualFocus }
            }

            MichiMenu {
                id: trackMenu
                MenuItem {
                    text: qsTr("Remove from playlist")
                    onTriggered: root.removeTrackRequested(index)
                }
                MenuItem {
                    text: qsTr("Move Up")
                    enabled: index > 0
                    onTriggered: root.moveTrackRequested(index, index - 1)
                }
                MenuItem {
                    text: qsTr("Move Down")
                    enabled: index < root.rows.length - 1
                    onTriggered: root.moveTrackRequested(index, index + 1)
                }
            }
        }
    }

    function formatTime(ms) {
        var totalSeconds = Math.round(ms / 1000)
        var minutes = Math.floor(totalSeconds / 60)
        var seconds = totalSeconds % 60
        return minutes + ":" + (seconds < 10 ? "0" : "") + seconds
    }
}
