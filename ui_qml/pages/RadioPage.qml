import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property string _filterText: ""
    property bool _showAddStation: false
    property string _newName: ""
    property string _newUrl: ""

    function doSearch(text) {
        _filterText = text.toLowerCase()
    }

    function addStationFromUI() {
        var notif = typeof notificationBridge !== "undefined" ? notificationBridge : null
        if (root.rd && _newUrl.trim()) {
            var result = root.rd.addStation(_newName.trim() || "New station", _newUrl.trim(), "MP3", "")
            if (result && result.ok) {
                _newName = ""; _newUrl = ""; _showAddStation = false
                if (notif) notif.showMessage("Emisora añadida", "success")
            } else {
                if (notif) notif.showMessage("Error: " + (result ? result.error : "desconocido"), "error")
            }
        }
    }

    Component.onCompleted: {
        if (root.rd && typeof root.rd.refresh !== "undefined")
            root.rd.refresh()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            HeroMaterial {
                width: parent.width; height: 140; radius: 16; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: "Radio"; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: "Emisoras de todo el mundo."; color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            SearchField {
                width: parent.width
                placeholderText: "Buscar emisoras..."
                onSearchTextChanged: root.doSearch(text)
            }

            SectionHeader { text: "Favoritas"; width: parent.width }

            Repeater {
                model: root.rd ? root.rd.favorites : []

                GlassCard {
                    width: parent.width; height: 60
                    title: modelData.name || ""
                    subtitle: modelData.codec ? modelData.codec + (modelData.country ? " · " + modelData.country : "") : ""
                    variant: "base"
                    interactive: true
                    onClicked: {
                        if (root.rd && typeof root.rd.playStation !== "undefined")
                            root.rd.playStation(modelData.url)
                    }
                }
            }

            Text {
                text: "No hay emisoras favoritas."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap
                visible: root.rd && root.rd.favorites.length === 0
            }

            SectionHeader { text: "Todas las emisoras"; width: parent.width }

            ListView {
                width: parent.width; height: Math.min(400, contentHeight)
                model: root.rd ? root.rd.stations : []
                clip: true
                visible: root.rd ? root.rd.stations.length > 0 : false

                delegate: GlassCard {
                    width: ListView.view.width; height: 60
                    title: modelData.name || ""
                    subtitle: modelData.codec ? modelData.codec + (modelData.country ? " · " + modelData.country : "") : modelData.url || ""
                    variant: "base"
                    interactive: true
                    visible: {
                        if (root._filterText === "") return true
                        var name = (modelData.name || "").toLowerCase()
                        var tags = (modelData.tags || []).join(" ").toLowerCase()
                        return name.indexOf(root._filterText) >= 0 || tags.indexOf(root._filterText) >= 0
                    }
                    onClicked: {
                        if (root.rd && typeof root.rd.playStation !== "undefined")
                            root.rd.playStation(modelData.url)
                    }
                }
            }

            Text {
                text: root._filterText !== ""
                      ? "No se encontraron emisoras para \"" + root._filterText + "\""
                      : "No hay emisoras configuradas."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap
                visible: root.rd && root.rd.stations.length === 0
            }

            MichiButton {
                text: _showAddStation ? "Cancelar" : "Añadir emisora"
                variant: "ghost"
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: _showAddStation = !_showAddStation
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.sm
                visible: _showAddStation

                Rectangle { width: parent.width; height: 1; color: MichiTheme.colors.borderSubtle }

                SearchField { placeholderText: "Nombre"; width: parent.width; onSearchTextChanged: _newName = text }
                SearchField { placeholderText: "URL del stream"; width: parent.width; onSearchTextChanged: _newUrl = text }
                MichiButton { text: "Añadir"; variant: "primary"; anchors.horizontalCenter: parent.horizontalCenter; onClicked: addStationFromUI() }
            }

            StatusBadge { text: "Radio QML"; kind: "info" }
        }
    }
}
