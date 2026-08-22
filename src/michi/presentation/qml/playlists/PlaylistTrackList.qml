import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../primitives"
import "../theme"

// PlaylistTrackList — quiet track rows with consistent music metadata,
// thumbnail artwork, and clear tabular layout matching the Hi-Fi design.
Item {
    id: root

    property var rows: []
    signal removeTrackRequested(int index)
    signal moveTrackRequested(int fromIndex, int toIndex)

    implicitHeight: 420
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Table Header
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 32
            Layout.leftMargin: MichiSpacing.md
            Layout.rightMargin: MichiSpacing.md
            spacing: MichiSpacing.md

            MichiText {
                text: "#"
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                Layout.preferredWidth: 28
                horizontalAlignment: Text.AlignRight
            }

            // Space corresponding to thumbnail artwork
            Item { Layout.preferredWidth: 36 }

            MichiText {
                text: qsTr("TITLE")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                Layout.fillWidth: true
                Layout.preferredWidth: 340
                Layout.minimumWidth: 180
            }

            MichiText {
                text: qsTr("ALBUM")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                Layout.fillWidth: true
                Layout.preferredWidth: 260
                Layout.minimumWidth: 140
            }

            MichiText {
                text: qsTr("DURATION")
                role: "technical"
                technical: true
                color: MichiPalette.textMuted
                Layout.preferredWidth: 64
                horizontalAlignment: Text.AlignRight
            }

            Item { Layout.preferredWidth: MichiMetrics.controlMedium }
        }

        // Header Divider Line
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: MichiSemanticColors.borderSubtle
            Layout.bottomMargin: MichiSpacing.xs
        }

        // Tracks ListView
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.rows
            spacing: 2
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: MichiScrollBar { }
            delegate: ItemDelegate {
                id: trackItem
                width: ListView.view.width
                height: 48
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.role: Accessible.ListItem
                Accessible.name: modelData.title + " — " + modelData.artist

                contentItem: RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: MichiSpacing.md
                    anchors.rightMargin: MichiSpacing.md
                    spacing: MichiSpacing.md

                    MichiText {
                        text: (index + 1)
                        role: "technical"
                        technical: true
                        color: MichiPalette.textMuted
                        Layout.preferredWidth: 28
                        horizontalAlignment: Text.AlignRight
                    }

                    // Track Thumbnail Artwork
                    Artwork {
                        Layout.preferredWidth: 36
                        Layout.preferredHeight: 36
                        sourcePath: modelData.artworkPath || ""
                        fallbackText: modelData.title || modelData.displayName || "T"
                        radius: MichiRadius.sm
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 340
                        Layout.minimumWidth: 180
                        spacing: 1
                        Layout.alignment: Qt.AlignVCenter

                        MichiText {
                            text: modelData.title
                            role: "body"
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            color: MichiPalette.textPrimary
                        }
                        MichiText {
                            visible: modelData.artist !== ""
                            text: modelData.artist
                            role: "caption"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            color: MichiPalette.textSecondary
                        }
                    }

                    MichiText {
                        text: modelData.album || "—"
                        role: "secondary"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                        Layout.preferredWidth: 260
                        Layout.minimumWidth: 140
                        color: MichiPalette.textSecondary
                    }

                    MichiText {
                        text: modelData.durationMs > 0 ? MichiFormat.formatDuration(modelData.durationMs) : ""
                        role: "technical"
                        technical: true
                        Layout.preferredWidth: 64
                        horizontalAlignment: Text.AlignRight
                        color: MichiPalette.textMuted
                    }

                    MichiIconButton {
                        iconName: "more"
                        accessibleName: qsTr("More options for ") + modelData.title
                        opacity: trackItem.hovered || trackItem.visualFocus ? 1 : 0
                        Behavior on opacity {
                            NumberAnimation { duration: MichiMotion.micro }
                        }
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
    }

}
