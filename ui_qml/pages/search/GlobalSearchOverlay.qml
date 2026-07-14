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
    signal closeRequested()

    function search(text) {
        root._query = text
        if (root._debounceTimer) root._debounceTimer = 0
        if (!text || text.trim() === "") {
            root._results = []
            root._searching = false
            return
        }
        root._searching = true
        if (root.bridge && typeof root.bridge.search !== "undefined") {
            var result = root.bridge.search(text)
            if (result && result.ok) {
                root._results = root.bridge.results || []
            }
        }
        root._searching = false
    }

    Rectangle {
        anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.5)

        MouseArea { anchors.fill: parent; onClicked: root.closeRequested() }
    }

    Rectangle {
        id: overlay; width: parent.width * 0.6; height: parent.height * 0.8
        anchors.centerIn: parent
        color: MichiTheme.colors.surface; radius: MichiTheme.radiusLg
        border.color: MichiTheme.colors.border; border.width: 1

        Column {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

            Row {
                width: parent.width; spacing: MichiTheme.spacing.sm
                SearchField {
                    id: searchField; width: parent.width - 80
                    placeholderText: "Buscar canciones, álbumes, artistas..."
                    onSearchTextChanged: root.search(text)
                }
                MichiButton { text: "Cerrar"; variant: "ghost"; onClicked: root.closeRequested() }
            }

            Repeater {
                model: root._results

                Rectangle {
                    width: parent.width; height: 36
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radiusSm

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                        Text {
                            width: 60; text: modelData.section || ""
                            color: MichiTheme.colors.accent; font.pixelSize: MichiTheme.typography.metaSize
                            font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width - 120; text: modelData.title || ""
                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: 60; text: modelData.subtitle || ""
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: mouseArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: root.navigateTo(modelData.type || "", modelData.id || "", modelData.title || "")
                    }
                }
            }

            Text {
                anchors.centerIn: parent; visible: root._searching
                text: "Buscando..."; color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
            }

            Text {
                anchors.centerIn: parent; visible: !root._searching && root._query !== "" && root._results.length === 0
                text: "Sin resultados para \"" + root._query + "\""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
            }
        }
    }
}
