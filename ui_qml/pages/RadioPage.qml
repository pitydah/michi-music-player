import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property string _filterText: ""

    function doSearch(text) {
        _filterText = text.toLowerCase()
    }

    Component.onCompleted: {
        if (root.radioBridge && typeof root.radioBridge.refresh !== "undefined")
            root.radioBridge.refresh()
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
                model: root.radioBridge ? root.radioBridge.favorites : []

                GlassCard {
                    width: parent.width; height: 60
                    title: modelData.name || ""
                    subtitle: modelData.codec ? modelData.codec + (modelData.country ? " · " + modelData.country : "") : ""
                    variant: "base"
                    interactive: true
                    onClicked: {
                        if (root.radioBridge && typeof root.radioBridge.playStation !== "undefined")
                            root.radioBridge.playStation(modelData.url)
                    }
                }
            }

            Text {
                text: "No hay emisoras favoritas."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap
                visible: root.radioBridge && root.radioBridge.favorites.length === 0
            }

            SectionHeader { text: "Todas las emisoras"; width: parent.width }

            Repeater {
                model: {
                    var all = root.radioBridge ? root.radioBridge.stations : []
                    if (root._filterText === "") return all
                    var filtered = []
                    for (var i = 0; i < all.length; i++) {
                        var name = (all[i].name || "").toLowerCase()
                        var tags = (all[i].tags || []).join(" ").toLowerCase()
                        if (name.indexOf(root._filterText) >= 0 || tags.indexOf(root._filterText) >= 0)
                            filtered.push(all[i])
                    }
                    return filtered
                }

                GlassCard {
                    width: parent.width; height: 60
                    title: modelData.name || ""
                    subtitle: modelData.codec ? modelData.codec + (modelData.country ? " · " + modelData.country : "") : modelData.url || ""
                    variant: "base"
                    interactive: true
                    onClicked: {
                        if (root.radioBridge && typeof root.radioBridge.playStation !== "undefined")
                            root.radioBridge.playStation(modelData.url)
                    }
                }
            }

            Text {
                text: root._filterText !== ""
                      ? "No se encontraron emisoras para \"" + root._filterText + "\""
                      : "No hay emisoras configuradas. Agrega una URL para comenzar."
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap
                visible: root.radioBridge && root.radioBridge.stations.length === 0
            }

            StatusBadge { text: "Interfaz clásica disponible"; kind: "info" }
        }
    }
}
