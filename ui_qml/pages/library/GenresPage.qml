import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Genres"
    objectName: "genresPage"
    focus: true
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _genres: []

    signal genreSelected(string genre)

    function reload() {
        if (root.lib && root.lib.getGenres) {
            root._genres = root.lib.getGenres() || []
        }
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                Text {
                    text: "Géneros"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { Layout.fillWidth: true }
            }
        }

        ListView {
            Accessible.role: Accessible.List

            Accessible.name: "ListView"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._genres
            clip: true; boundsBehavior: Flickable.StopAtBounds
            spacing: MichiTheme.spacing.xs

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: Item {
                width: parent.width; height: 40
                Rectangle {
                    anchors.fill: parent; color: mouse.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: typeof modelData === "object" ? modelData.name || modelData.genre : modelData
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Text {
                            text: typeof modelData === "object" && modelData.count ? modelData.count + " canciones" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        Text {
                            text: "▶"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: 12
                        }
                    }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.genreSelected(typeof modelData === "object" ? modelData.name || modelData.genre : modelData)
                    }
                }
            }
        }
    }
}
