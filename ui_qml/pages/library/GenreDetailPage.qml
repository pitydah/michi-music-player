import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Genre Detail"
    objectName: "genreDetailPage"
    focus: true
    id: root

    property string genre: ""
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null

    signal backRequested()

    function loadGenre(name) {
        genre = name
        if (root.lib && root.lib.setGenreFilter) {
            root.lib.setGenreFilter(name)
        }
    }

    LibraryPageStateGuard {
        anchors.fill: parent
        bridge: root.lib

        ColumnLayout {
            anchors.fill: parent; spacing: MichiTheme.spacing.lg
            anchors.margins: MichiTheme.spacing.xl

            RowLayout { spacing: MichiTheme.spacing.sm
                MichiButton { text: qsTr("\u2190 Volver"); variant: "ghost"; onClicked: root.backRequested() }
                Text {
                    text: qsTr("G\u00e9nero: ") + root.genre
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }
            }

            RowLayout { spacing: MichiTheme.spacing.sm
                MichiButton { text: qsTr("Reproducir todo"); variant: "primary"; onClicked: { if (root.lib && root.lib.playAllFiltered) root.lib.playAllFiltered() } }
                MichiButton { text: qsTr("Mezclar"); variant: "ghost" }
                MichiButton { text: qsTr("A\u00f1adir a cola"); variant: "ghost" }
            }

            SectionHeader { text: qsTr("Canciones en ") + root.genre; width: parent.width }

            ListView {
                Accessible.role: Accessible.List

                Accessible.name: "Canciones del género"

                activeFocusOnTab: true

                focusPolicy: Qt.StrongFocus
                Layout.fillWidth: true; Layout.fillHeight: true
                model: root.lib ? root.lib.trackModel : []
                clip: true; boundsBehavior: Flickable.StopAtBounds

                delegate: Item {
                    width: parent.width; height: 36
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
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
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: { if (root.lib && root.lib.playTrackById) root.lib.playTrackById(trackId || 0) }
                    }
                }
            }
        }
    }

    function formatDuration(secs) { var m = Math.floor(secs / 60); var s = Math.floor(secs % 60); return m + ":" + (s < 10 ? "0" : "") + s }
}
