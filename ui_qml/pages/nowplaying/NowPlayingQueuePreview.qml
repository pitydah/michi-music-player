import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Queue Preview"
    objectName: "nowPlayingQueuePreview"
    focus: true
    property var ps: null
    property var nav: null

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: "Cola"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
            }

            Item { Layout.fillWidth: true }

            Text {
                text: root.ps && root.ps.queue ? root.ps.queue.length + " pistas" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            MichiButton {
                text: "Ver todo"
                variant: "ghost"
                onClicked: { if (root.nav) root.nav.navigate("queue") }
            }
        }

        ListView {
            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.ps ? root.ps.queue : []
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            visible: root.ps && root.ps.queue && root.ps.queue.length > 0

            delegate: RowLayout {
                width: parent.width
                height: 24
                spacing: MichiTheme.spacing.sm

                Text {
                    text: (index + 1) + "."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    width: 24
                }

                Text {
                    text: modelData.title || "—"
                    color: modelData.is_current ? MichiTheme.colors.accent : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Text {
                    text: modelData.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    Layout.preferredWidth: parent.width * 0.3
                }
            }
        }

        Text {
            Layout.alignment: Qt.AlignCenter
            text: "Cola vacía"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            visible: !root.ps || !root.ps.queue || root.ps.queue.length === 0
        }
    }
}
