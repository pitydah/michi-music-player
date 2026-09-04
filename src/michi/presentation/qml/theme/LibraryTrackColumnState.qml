pragma Singleton
import QtQuick

// LIB-A §9/10/16/18: UNA autoridad de estado de columnas de la tabla.
// Jerarquía semántica formal (grupos): identity / context / audio /
// metadata / time / utility. Title es estructural (no ocultable); '#' es
// estructural también (nunca una columna de contenido). Presets
// productivos: essential / audiophile / metadata / minimal.
QtObject {
    id: root

    readonly property real numberWidth: 28

    property real artworkWidth: 44
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
    property real durationWidth: 80
    readonly property real actionsWidth: 74

    readonly property real artworkMinWidth: 30
    readonly property real artworkMaxWidth: 52
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
    readonly property real durationMinWidth: 76
    readonly property real actionsMinWidth: 74

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

    // LIB-A §10: Title es ESTRUCTURAL — nunca ocultable. La columna puede
    // redimensionarse pero no eliminarse.
    readonly property bool titleLocked: true
    // '#' es estructural (posición), no una columna de contenido.
    readonly property bool numberStructural: true

    // Columnas de contenido por grupo semántico (jerarquía formal §9).
    readonly property var columnsByGroup: ({
        identity: ["artwork", "title"],
        context: ["artist", "album"],
        audio: ["format", "sampleRate", "bitDepth", "dsdRate",
                "bitrate", "channels", "fileSize"],
        metadata: ["genre", "composer", "year"],
        time: ["duration"],
        utility: ["actions"]
    })

    // Columnas sortables (autoridad de la aplicación: library_track_query).
    readonly property var sortableColumns: [
        "title", "artist", "album", "format",
        "duration", "year", "genre", "composer",
        "sampleRate", "bitDepth", "bitrate", "channels", "fileSize"
    ]

    signal configurationChanged()

    function _visibleDefault(column) {
        return column === "artwork" || column === "title"
            || column === "artist" || column === "album"
            || column === "format" || column === "duration"
            || column === "actions"
    }

    function widthFor(column) {
        return root[column + "Width"]
    }

    function minimumWidthFor(column) {
        return root[column + "MinWidth"]
    }

    function isVisible(column) {
        if (column === "title")
            return true  // estructural: locked
        return root[column + "Visible"] === true
    }

    function setVisible(column, visible) {
        if (column === "title") {
            // LIB-A §10: no-op — el título nunca se oculta.
            return false
        }
        if (root[column + "Visible"] === undefined)
            return false
        if (root[column + "Visible"] === visible)
            return false
        root[column + "Visible"] = visible
        root.configurationChanged()
        return true
    }

    function setWidth(column, value) {
        if (root[column + "Width"] === undefined)
            return
        if (column === "actions")
            return
        var bounded = Math.max(minimumWidthFor(column), value)
        if (column === "artwork")
            bounded = Math.min(root.artworkMaxWidth, bounded)
        if (root[column + "Width"] !== bounded) {
            root[column + "Width"] = bounded
            root.configurationChanged()
        }
    }

    function resizeWithNeighbor(column, value, neighbor) {
        if (column === "actions" || neighbor === "actions")
            return
        if (root[column + "Width"] === undefined
                || root[neighbor + "Width"] === undefined)
            return
        var oldWidth = root[column + "Width"]
        var requested = Math.max(minimumWidthFor(column), value)
        if (column === "artwork")
            requested = Math.min(root.artworkMaxWidth, requested)
        var delta = requested - oldWidth
        var neighborWidth = root[neighbor + "Width"]
        var neighborMinimum = minimumWidthFor(neighbor)
        var compensation = delta > 0
            ? Math.min(delta, Math.max(0, neighborWidth - neighborMinimum)) : delta
        root[column + "Width"] = requested
        root[neighbor + "Width"] = neighborWidth - compensation
        root.configurationChanged()
    }

    function resetWidth(column) {
        var defaults = {
            artwork: 44, title: 300, artist: 190, album: 230, format: 88,
            sampleRate: 100, bitDepth: 82, dsdRate: 92, bitrate: 90, channels: 82,
            fileSize: 90, genre: 150, composer: 180, year: 68,
            duration: 80, actions: 74
        }
        if (defaults[column] !== undefined && column !== "actions") {
            root[column + "Width"] = defaults[column]
            root.configurationChanged()
        }
    }

    function resetWidths() {
        var columns = ["artwork", "title", "artist", "album", "format",
            "sampleRate", "bitDepth", "dsdRate", "bitrate", "channels", "fileSize",
            "genre", "composer", "year", "duration", "actions"]
        for (var index = 0; index < columns.length; ++index)
            root.resetWidth(columns[index])
    }

    // LIB-A §16: presets productivos. El preset fija las columnas de
    // contenido; las exclusiones de perfil (álbum/artista implícitos) las
    // aplica el header con showAlbumColumn/showArtistColumn.
    function _applyPresetVisible(preset) {
        root.artworkVisible = preset.artwork
        root.artistVisible = preset.artist
        root.albumVisible = preset.album
        root.formatVisible = preset.format
        root.sampleRateVisible = preset.sampleRate
        root.bitDepthVisible = preset.bitDepth
        root.dsdRateVisible = preset.dsdRate
        root.bitrateVisible = preset.bitrate
        root.channelsVisible = preset.channels
        root.fileSizeVisible = preset.fileSize
        root.genreVisible = preset.genre
        root.composerVisible = preset.composer
        root.yearVisible = preset.year
        root.durationVisible = preset.duration
        root.actionsVisible = preset.actions
        // title siempre visible (locked).
        root.titleVisible = true
        root.configurationChanged()
    }

    function applyPreset(name) {
        var presets = {
            "essential": {
                artwork: true, artist: true, album: true, format: true,
                sampleRate: false, bitDepth: false, dsdRate: false,
                bitrate: false, channels: false, fileSize: false,
                genre: false, composer: false, year: false,
                duration: true, actions: true
            },
            "audiophile": {
                artwork: false, artist: true, album: true, format: true,
                sampleRate: true, bitDepth: true, dsdRate: true,
                bitrate: true, channels: true, fileSize: false,
                genre: false, composer: false, year: false,
                duration: true, actions: true
            },
            "metadata": {
                artwork: false, artist: true, album: true, format: true,
                sampleRate: false, bitDepth: false, dsdRate: false,
                bitrate: false, channels: false, fileSize: false,
                genre: true, composer: true, year: true,
                duration: true, actions: true
            },
            "minimal": {
                artwork: false, artist: true, album: false, format: false,
                sampleRate: false, bitDepth: false, dsdRate: false,
                bitrate: false, channels: false, fileSize: false,
                genre: false, composer: false, year: false,
                duration: true, actions: true
            }
        }
        if (presets[name] === undefined)
            return false
        root._applyPresetVisible(presets[name])
        return true
    }

    function restoreDefaultColumns() {
        root.artworkVisible = true
        root.titleVisible = true
        root.artistVisible = true
        root.albumVisible = true
        root.formatVisible = true
        root.sampleRateVisible = false
        root.bitDepthVisible = false
        root.dsdRateVisible = false
        root.bitrateVisible = false
        root.channelsVisible = false
        root.fileSizeVisible = false
        root.genreVisible = false
        root.composerVisible = false
        root.yearVisible = false
        root.durationVisible = true
        root.actionsVisible = true
        root.configurationChanged()
    }

    function currentPreset() {
        if (!root.artistVisible || !root.albumVisible || !root.formatVisible
                || !root.durationVisible)
            return root.artistVisible && !root.albumVisible
                && !root.formatVisible && root.durationVisible
                ? "minimal" : ""
        if (!root.sampleRateVisible && !root.bitDepthVisible
                && !root.dsdRateVisible && !root.bitrateVisible
                && !root.channelsVisible && !root.fileSizeVisible
                && !root.genreVisible && !root.composerVisible
                && !root.yearVisible)
            return "essential"
        if (root.sampleRateVisible && root.bitDepthVisible
                && root.dsdRateVisible && root.bitrateVisible
                && root.channelsVisible && !root.genreVisible
                && !root.composerVisible && !root.yearVisible)
            return "audiophile"
        if (root.genreVisible && root.composerVisible && root.yearVisible)
            return "metadata"
        return ""
    }

    // Snapshot para persistencia (§19) — configuración completa sin
    // secrets internos.
    function snapshot() {
        var visible = {}
        var widths = {}
        var columns = ["artwork", "title", "artist", "album", "format",
            "sampleRate", "bitDepth", "dsdRate", "bitrate", "channels", "fileSize",
            "genre", "composer", "year", "duration", "actions"]
        for (var index = 0; index < columns.length; ++index) {
            var column = columns[index]
            visible[column] = root[column + "Visible"]
            widths[column] = root[column + "Width"]
        }
        return {
            "preset": root.currentPreset(),
            "visible": visible,
            "widths": widths
        }
    }

    // Aplica una configuración persistida (merge-safe: columnas faltantes
    // conservan el estado actual; nunca oculta title).
    function applyConfiguration(config) {
        if (config === null || config === undefined)
            return false
        var visible = config["visible"]
        var widths = config["widths"]
        if (visible !== undefined && visible !== null) {
            var keys = Object.keys(visible)
            for (var i = 0; i < keys.length; ++i) {
                var column = keys[i]
                if (column === "title")
                    continue  // locked
                if (root[column + "Visible"] !== undefined)
                    root[column + "Visible"] = !!visible[column]
            }
        }
        if (widths !== undefined && widths !== null) {
            var widthKeys = Object.keys(widths)
            for (var j = 0; j < widthKeys.length; ++j) {
                var widthColumn = widthKeys[j]
                var value = widths[widthColumn]
                if (typeof value === "number" && value > 0
                        && root[widthColumn + "Width"] !== undefined
                        && widthColumn !== "actions")
                    root[widthColumn + "Width"] = value
            }
        }
        root.configurationChanged()
        return true
    }
}
