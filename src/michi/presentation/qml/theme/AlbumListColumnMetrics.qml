pragma Singleton
import QtQuick

// POST-R4 P5: UNA autoridad de geometría para la Studio List (header y
// row consumen EXACTAMENTE las mismas métricas: artwork, título, artista,
// año, tracks, duración, formato). Prohibido recalcular anchos en cada
// lado con fórmulas independientes.
QtObject {
    readonly property real titleMaxWidthTechnical: 560
    readonly property real titleMaxWidthBasic: 720
    readonly property real titleMinWidth: 220
    readonly property real artistMinWidth: 150
    readonly property real artistMaxWidth: 300
    readonly property real yearColumnWidth: 54
    readonly property real tracksColumnWidth: 48
    readonly property real durationColumnWidth: 58
    readonly property real formatColumnWidth: 160
    readonly property real artworkSmallWidth: 34
    readonly property real artworkStandardWidth: 44
    readonly property real artworkNoneWidth: 0

    // Estados de artwork coherentes header/row: none → 0, small → 34,
    // standard → 44 (nunca header 34 con row 0, ni 34 vs 44).
    function artworkWidth(size) {
        if (size === "standard")
            return artworkStandardWidth
        if (size === "none")
            return artworkNoneWidth
        return artworkSmallWidth
    }

    function titleWidth(listWidth, showTechnical) {
        var ratio = showTechnical ? 0.34 : 0.45
        var max = showTechnical ? titleMaxWidthTechnical : titleMaxWidthBasic
        return Math.min(max, Math.max(titleMinWidth, Math.round(listWidth * ratio)))
    }

    function artistWidth(listWidth) {
        return Math.min(
            artistMaxWidth, Math.max(artistMinWidth, Math.round(listWidth * 0.20)))
    }

    // Costo del packing de columnas (el view decide qué columnas muestran
    // con la MISMA escala que las métricas de render).
    function columnCost(key) {
        if (key === "artist") return 210
        if (key === "year") return yearColumnWidth
        if (key === "tracks") return tracksColumnWidth
        if (key === "duration") return durationColumnWidth
        if (key === "format") return formatColumnWidth
        return 0
    }
}
