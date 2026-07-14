import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: typeof globalSearchBridge !== "undefined" ? globalSearchBridge : null
    property string _query: ""
    property var _groupedResults: []
    property bool _searching: false

    function search(text) {
        root._query = text
        if (!text || text.trim() === "") {
            root._groupedResults = []
            root._searching = false
            return
        }
        root._searching = true
        if (root.bridge && typeof root.bridge.search !== "undefined") {
            var result = root.bridge.search(text)
            if (result && result.ok) {
                var items = root.bridge.results || []
                var groups = {}
                for (var i = 0; i < items.length; i++) {
                    var sec = items[i].section || "Otros"
                    if (!groups[sec]) groups[sec] = []
                    groups[sec].push(items[i])
                }
                var grouped = []
                for (var key in groups) {
                    grouped.push({section: key, items: groups[key]})
                }
                root._groupedResults = grouped
            }
        }
        root._searching = false
    }

    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.lg

        HeroMaterial {
            width: parent.width; height: 160; radius: MichiTheme.radiusLg; showGlow: true
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.md
                Text {
                    text: "Búsqueda global"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                }
                SearchField {
                    width: parent.width * 0.7
                    placeholderText: "Canciones, álbumes, artistas, playlists..."
                    onSearchTextChanged: root.search(text)
                }
            }
        }

        Text {
            visible: root._searching; text: "Buscando..."; color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
        }

        Text {
            visible: !root._searching && root._query !== "" && root._groupedResults.length === 0
            text: "Sin resultados para \"" + root._query + "\""
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
        }

        Flickable {
            width: parent.width; height: parent.height - 200
            contentHeight: resultsColumn.height + MichiTheme.spacing.lg
            clip: true; boundsBehavior: Flickable.StopAtBounds

            Column {
                id: resultsColumn; width: parent.width; spacing: MichiTheme.spacing.lg

                Repeater {
                    model: root._groupedResults

                    SearchResultGroup {
                        width: parent.width
                        sectionTitle: modelData.section || ""
                        items: modelData.items || []
                        bridge: root.bridge
                    }
                }
            }
        }
    }
}
