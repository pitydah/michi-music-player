import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Composer Detail"
    objectName: "composerDetailPage"
    focus: true
    id: root

    property string composer: ""
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    signal backRequested()

    function loadComposer(name) {
        composer = name
        if (root.lib && root.lib.setComposerFilter) {
            root.lib.setComposerFilter(name)
        }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: MichiTheme.spacing.lg
        anchors.margins: MichiTheme.spacing.xl

        RowLayout { spacing: MichiTheme.spacing.sm
            MichiButton { text: "← Volver"; variant: "ghost"; onClicked: root.backRequested() }
            Text {
                text: "Compositor: " + root.composer
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.heroTitleSize
                font.weight: FontWeight.Bold
            }
        }

        RowLayout { spacing: MichiTheme.spacing.sm
            MichiButton { text: "Reproducir todo"; variant: "primary" }
            MichiButton { text: "Mezclar"; variant: "ghost" }
        }

        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root.lib ? root.lib.trackModel : []
            clip: true

            delegate: Item {
                width: parent.width; height: 36
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                    Text {
                        text: title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        Layout.fillWidth: true; elide: Text.ElideRight
                    }
                    Text {
                        text: artist || ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        Layout.preferredWidth: 120; elide: Text.ElideRight
                    }
                    Text {
                        text: duration ? formatDuration(duration) : ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                    }
                }
                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
