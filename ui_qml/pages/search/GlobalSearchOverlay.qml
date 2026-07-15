import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: typeof globalSearchBridge !== "undefined" ? globalSearchBridge : null
    property string _query: ""
    property var _results: []
    property bool _searching: false
    property int _debounceTimer: 0

    signal navigateTo(string type, string id, string title)
    signal openFullSearch()
    signal closeRequested()

    objectName: "globalSearchOverlay"
    focus: true

    Accessible.role: Accessible.Dialog
    Accessible.name: "Búsqueda rápida"
    Accessible.description: "Búsqueda rápida con resultados limitados"

    function search(text) {
        root._query = text
        if (root._debounceTimer) {
            root._debounceTimer = 0
        }
        if (!text || text.trim() === "") {
            root._results = []
            root._searching = false
            return
        }
        root._searching = true
        root._debounceTimer = Qt.callLater(function() {
            if (root.bridge && typeof root.bridge.search !== "undefined") {
                var result = root.bridge.search(text)
                if (result && result.ok) {
                    root._results = root.bridge.results || []
                }
            }
            root._searching = false
        }, 300)
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark

        MouseArea {
            anchors.fill: parent
            onClicked: root.closeRequested()
        }
    }

    Rectangle {
        id: overlayPanel
        width: parent.width * 0.65
        height: Math.min(parent.height * 0.85, 500)
        anchors.horizontalCenter: parent.horizontalCenter
        y: -height
        color: MichiTheme.colors.surfacePopup
        radius: MichiTheme.radiusLg
        border.color: MichiTheme.colors.borderCard
        border.width: 1

        PropertyAnimation {
            target: overlayPanel
            property: "y"
            from: -overlayPanel.height
            to: parent.height * 0.1
            duration: MichiTheme.motion.normal
            easing.type: Easing.OutCubic
            running: root.visible
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                SearchField {
                    id: searchField
                    width: parent.width - 80
                    placeholderText: "Buscar canciones, álbumes, artistas..."
                    fieldFocused: true
                    onSearchTextChanged: root.search(text)
                    onSearchSubmitted: root.search(text)
                    onClearRequested: {
                        root._results = []
                        root._query = ""
                    }
                    objectName: "globalSearchOverlay.searchField"
                    Accessible.name: "Campo de búsqueda rápida"
                }

                MichiButton {
                    text: "Cerrar"
                    variant: "ghost"
                    onClicked: root.closeRequested()
                    objectName: "globalSearchOverlay.closeButton"
                    Accessible.name: "Cerrar búsqueda rápida"
                }
            }

            Flickable {
                width: parent.width
                height: parent.height - searchField.height - MichiTheme.spacing.md * 4
                clip: true
                contentHeight: resultsColumn.height

                Column {
                    id: resultsColumn
                    width: parent.width
                    spacing: MichiTheme.spacing.sm

                    Repeater {
                        model: root._searching ? 0 : root._getTopResults()

                        Rectangle {
                            width: parent.width
                            height: 36
                            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                            radius: MichiTheme.radiusSm

                            Row {
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.sm
                                spacing: MichiTheme.spacing.sm

                                Text {
                                    width: 70
                                    text: modelData.section || ""
                                    color: MichiTheme.colors.accent
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: MichiTheme.typography.weightMedium
                                    anchors.verticalCenter: parent.verticalCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    width: parent.width - 150
                                    text: modelData.title || ""
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    elide: Text.ElideRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    width: 80
                                    text: modelData.subtitle || ""
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: mouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.navigateTo(modelData.type || "", modelData.id || "", modelData.title || "")
                            }
                        }
                    }

                    Text {
                        width: parent.width
                        visible: root._searching
                        text: "Buscando..."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Text {
                        width: parent.width
                        visible: !root._searching && root._query !== "" && root._results.length === 0
                        text: "Sin resultados para \"" + root._query + "\""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                        horizontalAlignment: Text.AlignHCenter
                    }

                    Item {
                        width: parent.width
                        height: 44
                        visible: root._results.length > 0

                        Rectangle {
                            anchors.fill: parent
                            color: mouseArea2.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                            radius: MichiTheme.radiusSm

                            Text {
                                anchors.centerIn: parent
                                text: "Abrir búsqueda completa \u2192"
                                color: MichiTheme.colors.accent
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }

                            MouseArea {
                                id: mouseArea2
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.openFullSearch()
                            }

                            Keys.onReturnPressed: root.openFullSearch()
                            Keys.onEnterPressed: root.openFullSearch()
                            focus: true
                            activeFocusOnTab: false
                        }
                    }
                }
            }
        }
    }

    function _getTopResults() {
        if (root._results.length === 0) return []
        var sections = {}
        var items = root._results
        for (var i = 0; i < items.length; i++) {
            var s = items[i].section || "Otros"
            if (!sections[s]) sections[s] = []
            if (sections[s].length < 3) {
                sections[s].push(items[i])
            }
        }
        var flat = []
        for (var key in sections) {
            for (var j = 0; j < sections[key].length; j++) {
                flat.push(sections[key][j])
            }
        }
        return flat
    }
}
