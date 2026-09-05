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

    // LIB-A P1 §17: UNA función de clamp (interactiva, persistida y de
    // restore usan la misma) — ningún estado de sesión puede diferir del
    // estado recargado.
    readonly property real maxResizableWidth: 720

    function clampWidth(column, value) {
        if (root[column + "Width"] === undefined || value === undefined
                || value === null || typeof value !== "number"
                || !isFinite(value))
            return value
        var minimum = root.minimumWidthFor(column)
        if (column === "artwork")
            return Math.max(minimum,
                Math.min(root.artworkMaxWidth, value))
        return Math.max(minimum, Math.min(root.maxResizableWidth, value))
    }

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
        var bounded = root.clampWidth(column, value)
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
        var requested = root.clampWidth(column, value)
        var delta = requested - oldWidth
        var neighborWidth = root[neighbor + "Width"]
        var neighborClamped = root.clampWidth(neighbor, neighborWidth - delta)
        var compensation = neighborWidth - neighborClamped
        root[column + "Width"] = requested
        root[neighbor + "Width"] = neighborClamped
        if (requested !== oldWidth || neighborClamped !== neighborWidth)
            root.configurationChanged()
    }

    function _resetWidth(column, notify) {
        var defaults = {
            artwork: 44, title: 300, artist: 190, album: 230, format: 88,
            sampleRate: 100, bitDepth: 82, dsdRate: 92, bitrate: 90, channels: 82,
            fileSize: 90, genre: 150, composer: 180, year: 68,
            duration: 80, actions: 74
        }
        if (defaults[column] === undefined || column === "actions")
            return false
        var value = defaults[column]
        if (root[column + "Width"] !== value) {
            root[column + "Width"] = value
            if (notify)
                root.configurationChanged()
            return true
        }
        return false
    }

    function resetWidth(column) {
        root._resetWidth(column, true)
    }

    function _resetWidths(notify) {
        var changed = false
        var columns = ["artwork", "title", "artist", "album", "format",
            "sampleRate", "bitDepth", "dsdRate", "bitrate", "channels", "fileSize",
            "genre", "composer", "year", "duration", "actions"]
        for (var index = 0; index < columns.length; ++index)
            changed = root._resetWidth(columns[index], false) || changed
        if (changed && notify)
            root.configurationChanged()
        return changed
    }

    function resetWidths() {
        root._resetWidths(true)
    }

    // LIB-A P2-H: UNA definición canónica de presets — applyPreset() y
    // currentPreset() comparan contra la MISMA fuente (nunca inferencia
    // duplicada por separado).
    readonly property var presetDefinitions: ({
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
    })

    // LIB-A §16: presets productivos. El preset fija las columnas de
    // contenido; las exclusiones de perfil (álbum/artista implícitos) las
    // aplica el header con showAlbumColumn/showArtistColumn.
    function _applyPresetVisible(preset, notify) {
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
        if (notify)
            root.configurationChanged()
    }

    function applyPreset(name) {
        var preset = root.presetDefinitions[name]
        if (preset === undefined)
            return false
        root._applyPresetVisible(preset, true)
        return true
    }

    // LIB-A P1 §12/13: Restore Defaults = preset Essential (visibilidad)
    // + TODOS los anchos por defecto + Title visible → UN configurationChanged.
    function restoreDefaults() {
        root._applyPresetVisible(root.presetDefinitions["essential"], false)
        root._resetWidths(false)
        root.titleVisible = true
        root.configurationChanged()
        return true
    }

    // Alias de compatibilidad (callers históricos) — misma semántica real.
    function restoreDefaultColumns() {
        return root.restoreDefaults()
    }

    function currentPreset() {
        // Compara el estado visible actual contra la MISMA definición
        // canónica de applyPreset (P2-H) — el preset es el que coincide
        // exactamente; customizaciones → "".
        var names = ["essential", "audiophile", "metadata", "minimal"]
        for (var index = 0; index < names.length; ++index) {
            var name = names[index]
            var definition = root.presetDefinitions[name]
            if (root.artworkVisible === definition.artwork
                    && root.artistVisible === definition.artist
                    && root.albumVisible === definition.album
                    && root.formatVisible === definition.format
                    && root.sampleRateVisible === definition.sampleRate
                    && root.bitDepthVisible === definition.bitDepth
                    && root.dsdRateVisible === definition.dsdRate
                    && root.bitrateVisible === definition.bitrate
                    && root.channelsVisible === definition.channels
                    && root.fileSizeVisible === definition.fileSize
                    && root.genreVisible === definition.genre
                    && root.composerVisible === definition.composer
                    && root.yearVisible === definition.year
                    && root.durationVisible === definition.duration
                    && root.actionsVisible === definition.actions)
                return name
        }
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
    // conservan el estado actual; nunca oculta title). Todos los anchos
    // pasan por el MISMO clamp que el resize interactivo. emitChange=false
    // durante la hydration de arranque (nunca un loop de persistencia).
    function applyConfiguration(config, emitChange) {
        if (config === null || config === undefined)
            return false
        var notify = emitChange !== false
        var visible = config["visible"]
        var widths = config["widths"]
        if (visible !== undefined && visible !== null) {
            var keys = Object.keys(visible)
            for (var i = 0; i < keys.length; ++i) {
                var column = keys[i]
                if (column === "title")
                    continue  // locked
                if (typeof visible[column] !== "boolean")
                    continue
                if (root[column + "Visible"] !== undefined
                        && root[column + "Visible"] !== visible[column])
                    root[column + "Visible"] = visible[column]
            }
        }
        if (widths !== undefined && widths !== null) {
            var widthKeys = Object.keys(widths)
            for (var j = 0; j < widthKeys.length; ++j) {
                var widthColumn = widthKeys[j]
                var value = widths[widthColumn]
                if (typeof value !== "number" || !isFinite(value)
                        || root[widthColumn + "Width"] === undefined
                        || widthColumn === "actions")
                    continue
                // Clamp único: mínimo de la columna; máximo general 720
                // (artwork conserva su techo propio).
                var bounded = Math.max(root.minimumWidthFor(widthColumn), value)
                if (widthColumn === "artwork")
                    bounded = Math.min(root.artworkMaxWidth, bounded)
                else
                    bounded = Math.min(720, bounded)
                if (root[widthColumn + "Width"] !== bounded)
                    root[widthColumn + "Width"] = bounded
            }
        }
        if (notify)
            root.configurationChanged()
        return true
    }
}
