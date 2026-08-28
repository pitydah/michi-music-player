pragma Singleton
import QtQuick

QtObject {
    id: root
    readonly property real numberWidth: 28

    property real artworkWidth: 40
    property real titleWidth: 300
    property real artistWidth: 190
    property real albumWidth: 230
    property real formatWidth: 88
    property real sampleRateWidth: 100
    property real bitDepthWidth: 82
    property real dsdRateWidth: 92
    property real bitrateWidth: 90
    property real channelsWidth: 82
    property real fileSizeWidth: 90
    property real genreWidth: 150
    property real composerWidth: 180
    property real yearWidth: 68
    property real durationWidth: 64
    property real actionsWidth: 74

    readonly property real artworkMinWidth: 30
    readonly property real titleMinWidth: 220
    readonly property real artistMinWidth: 120
    readonly property real albumMinWidth: 140
    readonly property real formatMinWidth: 68
    readonly property real sampleRateMinWidth: 84
    readonly property real bitDepthMinWidth: 70
    readonly property real dsdRateMinWidth: 74
    readonly property real bitrateMinWidth: 74
    readonly property real channelsMinWidth: 70
    readonly property real fileSizeMinWidth: 74
    readonly property real genreMinWidth: 100
    readonly property real composerMinWidth: 120
    readonly property real yearMinWidth: 58
    readonly property real durationMinWidth: 56
    readonly property real actionsMinWidth: 40

    property bool artworkVisible: true
    property bool titleVisible: true
    property bool artistVisible: true
    property bool albumVisible: true
    property bool formatVisible: true
    property bool sampleRateVisible: false
    property bool bitDepthVisible: false
    property bool dsdRateVisible: false
    property bool bitrateVisible: false
    property bool channelsVisible: false
    property bool fileSizeVisible: false
    property bool genreVisible: false
    property bool composerVisible: false
    property bool yearVisible: false
    property bool durationVisible: true
    property bool actionsVisible: true

    function widthFor(column) {
        return root[column + "Width"]
    }

    function minimumWidthFor(column) {
        return root[column + "MinWidth"]
    }

    function setWidth(column, value) {
        if (root[column + "Width"] === undefined)
            return
        root[column + "Width"] = Math.max(minimumWidthFor(column), value)
    }

    function resetWidth(column) {
        var defaults = {
            artwork: 40, title: 300, artist: 190, album: 230, format: 88,
            sampleRate: 100, bitDepth: 82, dsdRate: 92, bitrate: 90, channels: 82,
            fileSize: 90, genre: 150, composer: 180, year: 68,
            duration: 64, actions: 74
        }
        if (defaults[column] !== undefined)
            root[column + "Width"] = defaults[column]
    }

    function resetWidths() {
        var columns = ["artwork", "title", "artist", "album", "format",
            "sampleRate", "bitDepth", "dsdRate", "bitrate", "channels", "fileSize",
            "genre", "composer", "year", "duration", "actions"]
        for (var index = 0; index < columns.length; ++index)
            resetWidth(columns[index])
    }

    function restoreDefaultColumns() {
        artworkVisible = true
        titleVisible = true
        artistVisible = true
        albumVisible = true
        formatVisible = true
        sampleRateVisible = false
        bitDepthVisible = false
        dsdRateVisible = false
        bitrateVisible = false
        channelsVisible = false
        fileSizeVisible = false
        genreVisible = false
        composerVisible = false
        yearVisible = false
        durationVisible = true
        actionsVisible = true
    }
}
