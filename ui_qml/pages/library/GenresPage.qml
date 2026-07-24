import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

LibrarySectionPage {
    objectName: "genresPage"
    focus: true
    id: root
    sectionTitle: qsTr("Géneros")
    sectionSubtitle: qsTr("Explora la biblioteca por estilo musical")
    sectionIcon: "songs"
    navigationIndex: 3

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _genres: []

    signal genreSelected(string genre)

    function reload() {
        if (root.lib && root.lib.getGenres) {
            root._genres = root.lib.getGenres() || []
        }
    }

    function openGenre(genre) {
        root.genreSelected(genre)
        if (typeof navigationBridge !== "undefined" && genre)
            navigationBridge.navigateWithParams("library.genre_detail", {genre: genre})
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
                    text: qsTr("Géneros")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { Layout.fillWidth: true }
            }
        }

        ListView {
            id: genreList
            Accessible.role: Accessible.List

            Accessible.name: "Lista de géneros"

            activeFocusOnTab: true

            focusPolicy: Qt.StrongFocus
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._genres
            clip: true; boundsBehavior: Flickable.StopAtBounds
            spacing: MichiTheme.spacing.xs

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            function activateCurrent() {
                if (currentIndex < 0 || currentIndex >= root._genres.length) return
                var value = root._genres[currentIndex]
                root.openGenre(typeof value === "object" ? value.name || value.genre : value)
            }

            Keys.onReturnPressed: function(event) { activateCurrent(); event.accepted = true }
            Keys.onEnterPressed: function(event) { activateCurrent(); event.accepted = true }
            Keys.onSpacePressed: function(event) { activateCurrent(); event.accepted = true }

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
                            text: qsTr("▶")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            Accessible.role: Accessible.Graphic
                            Accessible.name: "Abrir género"
                            Accessible.description: "Navegar a este género"
                        }
                    }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.openGenre(typeof modelData === "object" ? modelData.name || modelData.genre : modelData)
                    }
                }
            }
        }
    }
}
