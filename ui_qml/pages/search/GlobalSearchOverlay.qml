import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Global Search Overlay"
    objectName: "globalSearchOverlay"
    focus: true
    id: root

    property var bridge: typeof globalSearchBridge !== "undefined" ? globalSearchBridge : null
    property string _query: ""
    property var _results: []
    property bool _searching: false
    property int _requestGen: 0
    property int _debounceTimer: 0

    signal navigateTo(string type, string id, string title)
    signal closeRequested()
    signal openFullSearch()


    Accessible.description: "Presiona Escape para cerrar"

    function search(text) {
        root._requestGen++
        var gen = root._requestGen
        root._query = text

        if (root._debounceTimer) {
            root._debounceTimer = 0
        }

        if (!text || text.trim() === "") {
            root._results = []
            root._searching = false
            return
        }

        root._debounceTimer = Qt.callLater(function() {
            if (gen !== root._requestGen) return
            if (root._debounceTimer) {
                root._debounceTimer = 0
            }
            root._searching = true

            if (root.bridge && typeof root.bridge.search !== "undefined") {
                var result = root.bridge.search(text)
                if (gen !== root._requestGen) return
                if (result && result.ok) {
                    var allResults = root.bridge.results || []
                    var preview = {}
                    for (var i = 0; i < allResults.length; i++) {
                        var sec = allResults[i].section || "Otros"
                        if (!preview[sec]) preview[sec] = []
                        if (preview[sec].length < 3) preview[sec].push(allResults[i])
                    }
                    var flat = []
                    for (var secKey in preview) {
                        for (var j = 0; j < preview[secKey].length; j++) {
                            flat.push(preview[secKey][j])
                        }
                    }
                    root._results = flat
                }
            }
            root._searching = false
        }, 300)
    }

    function openFullSearchFromOverlay() {
        root.openFullSearch()
        root.closeRequested()
    }

    NumberAnimation on y {
        from: -root.height
        to: 0
        duration: MichiTheme.motionNormal
        easing.type: Easing.OutCubic
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.5)

        MouseArea {
            anchors.fill: parent
            onClicked: root.closeRequested()
            cursorShape: Qt.ArrowCursor
        }
    }

    Rectangle {
        id: overlay
        width: parent.width * 0.6
        height: Math.min(parent.height * 0.75, 500)
        anchors.horizontalCenter: parent.horizontalCenter
        y: MichiTheme.spacing.xl
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radiusLg
        border.color: MichiTheme.colors.borderCard
        border.width: 1


        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                SearchField {
                    Accessible.role: Accessible.EditableText

                    id: searchField
                    width: parent.width - 80
                    placeholderText: "Búsqueda rápida (Ctrl+F)..."
                    Accessible.description: "Escribe para buscar, muestra máximo 3 resultados por sección"
                    onSearchTextChanged: root.search(text)
                    activeFocusOnTab: true
                    Keys.onEscapePressed: root.closeRequested()
                    Keys.onReturnPressed: {
                        if (root._results.length > 0) {
                            root.navigateTo(root._results[0].type || "", root._results[0].id || "", root._results[0].title || "")
                        }
                    }
                }

                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                MichiButton {
                    text: "Cerrar"
                    variant: "ghost"
                    anchors.verticalCenter: parent.verticalCenter
                    Keys.onEscapePressed: root.closeRequested()
                    onClicked: root.closeRequested()
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
                visible: root._results.length > 0 || root._searching
            }

            Text {
                visible: root._searching
                text: "Buscando..."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Text {
                visible: !root._searching && root._query !== "" && root._results.length === 0
                text: "Sin resultados para \"" + root._query + "\""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Flickable {
                width: parent.width
                height: parent.height - 100
                contentHeight: previewColumn.height
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                visible: root._results.length > 0

                Column {
                    id: previewColumn
                    width: parent.width
                    spacing: MichiTheme.spacing.xs

                    Repeater {
                        model: root._results

                        SearchResultRow {
                            width: parent.width
                            rowType: modelData.type || ""
                            rowId: modelData.id || ""
                            rowTitle: modelData.title || ""
                            rowSubtitle: modelData.subtitle || ""
                            bridge: root.bridge
                            activeFocusOnTab: true
                            onClicked: root.navigateTo(modelData.type || "", modelData.id || "", modelData.title || "")
                            Keys.onReturnPressed: root.navigateTo(modelData.type || "", modelData.id || "", modelData.title || "")
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
                visible: root._results.length > 0
                Accessible.role: Accessible.Button

            }

            MichiButton {
                text: "Abrir búsqueda completa \u2192"
                variant: "ghost"
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root._results.length > 0
                activeFocusOnTab: true
                onClicked: root.openFullSearchFromOverlay()
                Keys.onReturnPressed: root.openFullSearchFromOverlay()
                Keys.onSpacePressed: root.openFullSearchFromOverlay()
            }
        }
    }

    Keys.onEscapePressed: root.closeRequested()
}
