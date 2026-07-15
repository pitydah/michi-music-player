import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    objectName: "mixGenerator.page"

>>>>>>> Stashed changes
    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    property string _state: "IDLE"
    property string _mixType: "daily_mix"
    property string _seedValue: ""
    property string _seedArtist: ""
    property string _qualityFilter: ""
    property string _genreFilter: ""
    property int _yearFrom: 0
    property int _yearTo: 0
    property int _durationMinutes: 30
    property int _trackLimit: 25
    property int _variety: 50
    property int _familiarity: 50
    property bool _avoidRecent: true
    property var _exclusions: []
    property var _resultSongs: []
    property int _progressCurrent: 0
    property int _progressTotal: 0
    property string _errorMessage: ""
    property string _statusMessage: ""

<<<<<<< Updated upstream
=======
    signal backClicked()
    signal generationComplete(var result)
=======
    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    property string _state: "IDLE"
    property string _mixType: "daily_mix"
    property string _seedValue: ""
    property string _seedArtist: ""
    property string _qualityFilter: ""
    property string _genreFilter: ""
    property int _yearFrom: 0
    property int _yearTo: 0
    property int _durationMinutes: 30
    property int _trackLimit: 25
    property int _variety: 50
    property int _familiarity: 50
    property bool _avoidRecent: true
    property var _exclusions: []
    property var _resultSongs: []
    property int _progressCurrent: 0
    property int _progressTotal: 0
    property string _errorMessage: ""
    property string _statusMessage: ""

>>>>>>> Stashed changes
    signal backRequested()
    signal showResults(var songs, string mixType)

    objectName: "MixGeneratorPage"
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    Accessible.role: Accessible.Pane
    Accessible.name: "Generador de Mix"

<<<<<<< Updated upstream
    function reset() {
        root._state = "IDLE"
        root._errorMessage = ""
        root._statusMessage = ""
        root._resultSongs = []
        root._progressCurrent = 0
        root._progressTotal = 0
    }
=======
<<<<<<< HEAD
    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "mixGenerator.focusScope"
>>>>>>> Stashed changes

    function validate() {
        root._state = "VALIDATING"
        root._errorMessage = ""
        root._statusMessage = "Validando configuración..."

        if (!root.mx) {
            root._state = "FAILED"
            root._errorMessage = "Servicio de mix no disponible"
            return false
        }

        if (root._mixType === "custom" && root._seedValue === "" && root._seedArtist === "") {
            root._state = "FAILED"
            root._errorMessage = "Selecciona un artista o introduce parámetros para el mix personalizado"
            return false
        }

        return true
    }

    function generate() {
        if (!validate()) return
        root._state = "GENERATING"
        root._statusMessage = "Generando mix..."
        root._resultSongs = []

        if (root.mx && typeof root.mx.loadMix === "function") {
            var params = {}
            if (root._seedValue) params.seed = root._seedValue
            if (root._seedArtist) params.seed_artist = root._seedArtist
            if (root._qualityFilter) params.quality = root._qualityFilter
            if (root._genreFilter) params.genre = root._genreFilter
            if (root._yearFrom > 0) params.year_from = root._yearFrom
            if (root._yearTo > 0) params.year_to = root._yearTo
            if (root._trackLimit > 0) params.limit = root._trackLimit
            if (root._avoidRecent) params.avoid_recent = true
            if (root._variety !== 50) params.variety = root._variety
            if (root._familiarity !== 50) params.familiarity = root._familiarity

            var seed = JSON.stringify(params)
            var result = root.mx.loadMix(root._mixType, seed)

            if (result && result.ok) {
                if (root.mx.currentSongs && root.mx.currentSongs.length > 0) {
                    root._resultSongs = root.mx.currentSongs
                    root._state = "READY"
                    root._statusMessage = "Mix generado: " + root._resultSongs.length + " canciones"
                } else {
                    root._state = "NO_CANDIDATES"
                    root._statusMessage = ""
                }
            } else {
                root._state = "FAILED"
                root._errorMessage = (result && result.error) || "Error al generar el mix"
            }
        } else {
            root._state = "FAILED"
            root._errorMessage = "Bridge no disponible"
        }
    }

    function cancelGeneration() {
        if (root._state !== "GENERATING") return
        root._state = "CANCELLING"
        root._statusMessage = "Cancelando generación..."

        if (root.mx && typeof root.mx.cancelGeneration === "function") {
            root.mx.cancelGeneration()
        }
        root._state = "CANCELLED"
        root._statusMessage = "Generación cancelada"
        root._resultSongs = []
    }

    function retry() {
        root.reset()
        root.generate()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: contentColumn; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    text: "Volver"; variant: "ghost"
                    objectName: "generatorBackButton"
                    Accessible.name: "Volver a Mix"
                    activeFocusOnTab: true
                    onClicked: root.backRequested()
                    KeyNavigation.tab: mixTypeCombo
                }

                Text {
                    text: "Generar Mix"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            InlineError {
                id: errorBanner
                width: parent.width
                message: root._errorMessage
                showDismiss: true
                onDismissed: root._errorMessage = ""
                visible: root._state === "FAILED" || root._state === "NO_CANDIDATES"
            }

            Row {
                spacing: MichiTheme.spacing.lg; width: parent.width

                Column {
                    spacing: MichiTheme.spacing.md; width: parent.width * 0.48

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Tipo de Mix"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        ComboBox {
                            id: mixTypeCombo; width: parent.width
                            objectName: "mixTypeCombo"
                            Accessible.name: "Tipo de Mix"
                            model: [
                                { text: "Mix diario", value: "daily_mix" },
                                { text: "Favoritos", value: "favorites" },
                                { text: "Recientes", value: "recent" },
                                { text: "No escuchadas", value: "unplayed" },
                                { text: "Más escuchadas", value: "most_played" },
                                { text: "Por artista", value: "by_artist" },
                                { text: "Por álbum", value: "by_album" },
                                { text: "Por género", value: "by_genre" },
                                { text: "Por década", value: "by_decade" },
                                { text: "Por año", value: "by_year" },
                                { text: "Alta calidad", value: "high_quality" },
                                { text: "Redescubrimiento", value: "rediscovery" },
                                { text: "Personalizado", value: "custom" }
                            ]
                            textRole: "text"
                            valueRole: "value"
                            currentIndex: 0
                            onCurrentValueChanged: root._mixType = currentValue
                            activeFocusOnTab: true
                            KeyNavigation.tab: seedField
                            KeyNavigation.backtab: generatorBackButton
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Seed (opcional)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: seedField; width: parent.width
                            objectName: "seedField"
                            Accessible.name: "Seed opcional para el mix"
                            placeholderText: "Parámetros en JSON (ej: {\"artist\":\"Genesis\"})"
                            text: root._seedValue
                            onTextChanged: root._seedValue = text
                            activeFocusOnTab: true
                            KeyNavigation.tab: seedArtistField
                            KeyNavigation.backtab: mixTypeCombo
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Artista semilla"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: seedArtistField; width: parent.width
                            objectName: "seedArtistField"
                            Accessible.name: "Artista semilla para el mix"
                            placeholderText: "Nombre del artista"
                            text: root._seedArtist
                            onTextChanged: root._seedArtist = text
                            activeFocusOnTab: true
                            KeyNavigation.tab: exclusionsField
                            KeyNavigation.backtab: seedField
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Exclusiones (separadas por coma)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: exclusionsField; width: parent.width
                            objectName: "exclusionsField"
                            Accessible.name: "Exclusiones separadas por coma"
                            placeholderText: "artista1, artista2, género1"
                            onTextChanged: {
                                root._exclusions = text.split(",").map(function(x) { return x.trim() }).filter(function(x) { return x !== "" })
                            }
                            activeFocusOnTab: true
                            KeyNavigation.tab: qualityCombo
                            KeyNavigation.backtab: seedArtistField
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.md; width: parent.width * 0.48

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Duración (min)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: durationSpin; width: parent.width; from: 5; to: 480; stepSize: 5; value: root._durationMinutes
                                objectName: "durationSpin"
                                Accessible.name: "Duración del mix en minutos"
                                onValueChanged: root._durationMinutes = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: trackLimitSpin
                                KeyNavigation.backtab: exclusionsField
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Límite pistas"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: trackLimitSpin; width: parent.width; from: 5; to: 200; value: root._trackLimit
                                objectName: "trackLimitSpin"
                                Accessible.name: "Límite máximo de pistas"
                                onValueChanged: root._trackLimit = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: qualityCombo
                                KeyNavigation.backtab: durationSpin
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Variedad"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                Slider {
                                    id: varietySlider; width: 120; from: 0; to: 100; value: root._variety
                                    objectName: "varietySlider"
                                    Accessible.name: "Variedad del mix"
                                    onValueChanged: root._variety = value
                                    activeFocusOnTab: true
                                    KeyNavigation.tab: familiaritySlider
                                    KeyNavigation.backtab: trackLimitSpin
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._variety; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Familiaridad"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                Slider {
                                    id: familiaritySlider; width: 120; from: 0; to: 100; value: root._familiarity
                                    objectName: "familiaritySlider"
                                    Accessible.name: "Familiaridad del mix"
                                    onValueChanged: root._familiarity = value
                                    activeFocusOnTab: true
                                    KeyNavigation.tab: avoidRecentCheck
                                    KeyNavigation.backtab: varietySlider
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._familiarity; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Calidad mínima"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            ComboBox {
                                id: qualityCombo; width: parent.width
                                objectName: "qualityCombo"
                                Accessible.name: "Filtro de calidad mínima"
                                model: [
                                    { text: "Cualquiera", value: "" },
                                    { text: ">= 192 kbps", value: "192" },
                                    { text: ">= 320 kbps", value: "320" },
                                    { text: "Lossless (FLAC)", value: "lossless" }
                                ]
                                textRole: "text"; valueRole: "value"
                                currentIndex: 0
                                onCurrentValueChanged: root._qualityFilter = currentValue
                                activeFocusOnTab: true
                                KeyNavigation.tab: genreCombo
                                KeyNavigation.backtab: familiaritySlider
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Género"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            ComboBox {
                                id: genreCombo; width: parent.width
                                objectName: "genreCombo"
                                Accessible.name: "Filtro de género"
                                model: [
                                    { text: "Cualquiera", value: "" },
                                    { text: "Rock", value: "rock" },
                                    { text: "Pop", value: "pop" },
                                    { text: "Jazz", value: "jazz" },
                                    { text: "Clásica", value: "classical" },
                                    { text: "Electrónica", value: "electronic" },
                                    { text: "Hip Hop", value: "hip hop" },
                                    { text: "R&B", value: "rnb" },
                                    { text: "Metal", value: "metal" },
                                    { text: "Folk", value: "folk" },
                                    { text: "Blues", value: "blues" },
                                    { text: "Country", value: "country" },
                                    { text: "Latina", value: "latin" },
                                    { text: "Reggae", value: "reggae" }
                                ]
                                textRole: "text"; valueRole: "value"
                                currentIndex: 0
                                onCurrentValueChanged: root._genreFilter = currentValue
                                activeFocusOnTab: true
                                KeyNavigation.tab: yearFromSpin
                                KeyNavigation.backtab: qualityCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Año desde"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: yearFromSpin; width: parent.width; from: 1900; to: 2030; value: root._yearFrom
                                objectName: "yearFromSpin"
                                Accessible.name: "Año inicial del filtro"
                                onValueChanged: root._yearFrom = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: yearToSpin
                                KeyNavigation.backtab: genreCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Año hasta"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: yearToSpin; width: parent.width; from: 1900; to: 2030; value: root._yearTo
                                objectName: "yearToSpin"
                                Accessible.name: "Año final del filtro"
                                onValueChanged: root._yearTo = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: avoidRecentCheck
                                KeyNavigation.backtab: yearFromSpin
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    CheckBox {
                        id: avoidRecentCheck
                        text: "Evitar escuchadas recientemente"
                        checked: root._avoidRecent
                        objectName: "avoidRecentCheck"
                        Accessible.name: "Evitar canciones escuchadas recientemente"
                        onCheckedChanged: root._avoidRecent = checked
                        activeFocusOnTab: true
                        KeyNavigation.tab: generateBtn
                        KeyNavigation.backtab: yearToSpin
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md; width: parent.width

                MichiButton {
                    id: generateBtn
                    text: {
                        if (root._state === "VALIDATING") return "Validando..."
                        if (root._state === "GENERATING") return "Generando..."
                        if (root._state === "CANCELLING") return "Cancelando..."
                        if (root._state === "CANCELLED") return "Regenerar"
                        if (root._state === "NO_CANDIDATES") return "Reintentar"
                        if (root._state === "FAILED") return "Reintentar"
                        return "Generar Mix"
                    }
                    variant: root._state === "FAILED" ? "danger" : "primary"
                    objectName: "generateBtn"
                    Accessible.name: text
                    activeFocusOnTab: true
                    enabled: root._state !== "VALIDATING" && root._state !== "GENERATING" && root._state !== "CANCELLING"
                    KeyNavigation.tab: cancelBtn
                    KeyNavigation.backtab: avoidRecentCheck

                    onClicked: {
                        if (root._state === "CANCELLED" || root._state === "NO_CANDIDATES") {
                            root.retry()
                        } else {
                            root.generate()
                        }
                    }
                }

                MichiButton {
                    id: cancelBtn
                    text: "Cancelar"
                    variant: "danger"
                    objectName: "cancelBtn"
                    Accessible.name: "Cancelar generación"
                    activeFocusOnTab: true
                    visible: root._state === "GENERATING"
                    KeyNavigation.tab: resultList
                    KeyNavigation.backtab: generateBtn

                    onClicked: root.cancelGeneration()
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "GENERATING" || root._state === "CANCELLING" || root._state === "CANCELLED"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: root._statusMessage; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        MichiProgressBar {
                            width: parent.width
                            from: 0; to: root._progressTotal > 0 ? root._progressTotal : 100
                            value: root._progressCurrent
                            indeterminate: root._state === "GENERATING" && root._progressTotal === 0
                            accessibleName: "Progreso de generación"
                        }

                        Text {
                            text: root._progressTotal > 0
                                ? root._progressCurrent + " / " + root._progressTotal + " canciones"
                                : "Buscando canciones..."
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "NO_CANDIDATES"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: "No se encontraron candidatos"; color: MichiTheme.colors.warning
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: "Prueba con una selección diferente o ajusta los filtros."
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap; width: parent.width
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "CANCELLED"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Generación cancelada"; color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: "Puedes ajustar los parámetros y generar de nuevo."
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "READY"

                SectionHeader {
                    text: "Mix generado — " + root._resultSongs.length + " canciones"
                    width: parent.width
                }

                ListView {
                    id: resultList
                    width: parent.width; height: Math.min(360, root._resultSongs.length * 48)
                    model: root._resultSongs; clip: true; spacing: 2
                    activeFocusOnTab: true
                    objectName: "generatedSongsList"
                    Accessible.name: "Canciones generadas"

                    delegate: Rectangle {
                        width: parent.width; height: 44
                        color: modelData._hovered ? MichiTheme.colors.surfaceHover : "transparent"
                        radius: MichiTheme.radiusSm
                        activeFocusOnTab: true
                        objectName: "generatedSongItem_" + index
                        Accessible.name: modelData.title + " - " + modelData.artist
                        KeyNavigation.tab: index < root._resultSongs.length - 1
                            ? resultList.itemAtIndex(index + 1)
                            : showResultsBtn
                        KeyNavigation.backtab: index > 0
                            ? resultList.itemAtIndex(index - 1)
                            : cancelBtn

                        Keys.onReturnPressed: onClick()
                        Keys.onSpacePressed: onClick()

                        property bool _hovered: false

                        signal onClick()

                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                            Text {
                                width: parent.width * 0.35; text: modelData.title || ""
                                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: parent.width * 0.25; text: modelData.artist || ""
                                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: parent.width * 0.20; text: modelData.album || ""
                                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: 24; text: "P"; color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.mx && typeof root.mx.playFromIndex === "function")
                                            root.mx.playFromIndex(index)
                                    }
                                }
                            }

                            Text {
                                width: 24; text: "+"; color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.cardTitleSize; anchors.verticalCenter: parent.verticalCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.mx && typeof root.mx.enqueueTrack === "function")
                                            root.mx.enqueueTrack(index)
                                    }
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true
                            onEntered: modelData._hovered = true
                            onExited: modelData._hovered = false
                        }
                    }

                    Text {
                        anchors.centerIn: parent; visible: parent.count === 0
                        text: "No hay canciones generadas"
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    }
                }

                Row {
                    id: resultActionsRow
                    spacing: MichiTheme.spacing.sm; width: parent.width

                    MichiButton {
                        id: showResultsBtn
                        text: "Ver resultados completos"; variant: "primary"
                        objectName: "showResultsBtn"
                        Accessible.name: "Ver resultados completos del mix"
                        activeFocusOnTab: true
                        KeyNavigation.tab: regenerateFromResultBtn
                        KeyNavigation.backtab: resultList
                        onClicked: root.showResults(root._resultSongs, root._mixType)
                    }

                    MichiButton {
                        id: regenerateFromResultBtn
                        text: "Regenerar"; variant: "ghost"
                        objectName: "regenerateFromResultBtn"
                        Accessible.name: "Regenerar mix"
                        activeFocusOnTab: true
                        KeyNavigation.tab: showResultsBtn
                        KeyNavigation.backtab: showResultsBtn
                        onClicked: root.retry()
                    }
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: "Bridge no disponible — funcionalidad limitada"
                kind: "disconnected"
            }
<<<<<<< Updated upstream
=======
        } catch (e) {
            root.state = "FAILED"
            root._errorMsg = "Error: " + e.message
        }
    }

    function _cancelGeneration() {
        if (!root.mx) return
        root.state = "CANCELLING"
        try {
            var result = root.mx.cancelGeneration()
            root.state = "CANCELLED"
            root._errorMsg = result && result.ok ? "Generación cancelada" : "Error al cancelar"
        } catch (e) {
            root.state = "CANCELLED"
            root._errorMsg = "Cancelado"
=======
    function reset() {
        root._state = "IDLE"
        root._errorMessage = ""
        root._statusMessage = ""
        root._resultSongs = []
        root._progressCurrent = 0
        root._progressTotal = 0
    }

    function validate() {
        root._state = "VALIDATING"
        root._errorMessage = ""
        root._statusMessage = "Validando configuración..."

        if (!root.mx) {
            root._state = "FAILED"
            root._errorMessage = "Servicio de mix no disponible"
            return false
        }

        if (root._mixType === "custom" && root._seedValue === "" && root._seedArtist === "") {
            root._state = "FAILED"
            root._errorMessage = "Selecciona un artista o introduce parámetros para el mix personalizado"
            return false
        }

        return true
    }

    function generate() {
        if (!validate()) return
        root._state = "GENERATING"
        root._statusMessage = "Generando mix..."
        root._resultSongs = []

        if (root.mx && typeof root.mx.loadMix === "function") {
            var params = {}
            if (root._seedValue) params.seed = root._seedValue
            if (root._seedArtist) params.seed_artist = root._seedArtist
            if (root._qualityFilter) params.quality = root._qualityFilter
            if (root._genreFilter) params.genre = root._genreFilter
            if (root._yearFrom > 0) params.year_from = root._yearFrom
            if (root._yearTo > 0) params.year_to = root._yearTo
            if (root._trackLimit > 0) params.limit = root._trackLimit
            if (root._avoidRecent) params.avoid_recent = true
            if (root._variety !== 50) params.variety = root._variety
            if (root._familiarity !== 50) params.familiarity = root._familiarity

            var seed = JSON.stringify(params)
            var result = root.mx.loadMix(root._mixType, seed)

            if (result && result.ok) {
                if (root.mx.currentSongs && root.mx.currentSongs.length > 0) {
                    root._resultSongs = root.mx.currentSongs
                    root._state = "READY"
                    root._statusMessage = "Mix generado: " + root._resultSongs.length + " canciones"
                } else {
                    root._state = "NO_CANDIDATES"
                    root._statusMessage = ""
                }
            } else {
                root._state = "FAILED"
                root._errorMessage = (result && result.error) || "Error al generar el mix"
            }
        } else {
            root._state = "FAILED"
            root._errorMessage = "Bridge no disponible"
        }
    }

    function cancelGeneration() {
        if (root._state !== "GENERATING") return
        root._state = "CANCELLING"
        root._statusMessage = "Cancelando generación..."

        if (root.mx && typeof root.mx.cancelGeneration === "function") {
            root.mx.cancelGeneration()
        }
        root._state = "CANCELLED"
        root._statusMessage = "Generación cancelada"
        root._resultSongs = []
    }

    function retry() {
        root.reset()
        root.generate()
    }

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: contentColumn.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: contentColumn; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm; width: parent.width

                MichiButton {
                    text: "Volver"; variant: "ghost"
                    objectName: "generatorBackButton"
                    Accessible.name: "Volver a Mix"
                    activeFocusOnTab: true
                    onClicked: root.backRequested()
                    KeyNavigation.tab: mixTypeCombo
                }

                Text {
                    text: "Generar Mix"; color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            InlineError {
                id: errorBanner
                width: parent.width
                message: root._errorMessage
                showDismiss: true
                onDismissed: root._errorMessage = ""
                visible: root._state === "FAILED" || root._state === "NO_CANDIDATES"
            }

            Row {
                spacing: MichiTheme.spacing.lg; width: parent.width

                Column {
                    spacing: MichiTheme.spacing.md; width: parent.width * 0.48

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Tipo de Mix"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        ComboBox {
                            id: mixTypeCombo; width: parent.width
                            objectName: "mixTypeCombo"
                            Accessible.name: "Tipo de Mix"
                            model: [
                                { text: "Mix diario", value: "daily_mix" },
                                { text: "Favoritos", value: "favorites" },
                                { text: "Recientes", value: "recent" },
                                { text: "No escuchadas", value: "unplayed" },
                                { text: "Más escuchadas", value: "most_played" },
                                { text: "Por artista", value: "by_artist" },
                                { text: "Por álbum", value: "by_album" },
                                { text: "Por género", value: "by_genre" },
                                { text: "Por década", value: "by_decade" },
                                { text: "Por año", value: "by_year" },
                                { text: "Alta calidad", value: "high_quality" },
                                { text: "Redescubrimiento", value: "rediscovery" },
                                { text: "Personalizado", value: "custom" }
                            ]
                            textRole: "text"
                            valueRole: "value"
                            currentIndex: 0
                            onCurrentValueChanged: root._mixType = currentValue
                            activeFocusOnTab: true
                            KeyNavigation.tab: seedField
                            KeyNavigation.backtab: generatorBackButton
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Seed (opcional)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: seedField; width: parent.width
                            objectName: "seedField"
                            Accessible.name: "Seed opcional para el mix"
                            placeholderText: "Parámetros en JSON (ej: {\"artist\":\"Genesis\"})"
                            text: root._seedValue
                            onTextChanged: root._seedValue = text
                            activeFocusOnTab: true
                            KeyNavigation.tab: seedArtistField
                            KeyNavigation.backtab: mixTypeCombo
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Artista semilla"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: seedArtistField; width: parent.width
                            objectName: "seedArtistField"
                            Accessible.name: "Artista semilla para el mix"
                            placeholderText: "Nombre del artista"
                            text: root._seedArtist
                            onTextChanged: root._seedArtist = text
                            activeFocusOnTab: true
                            KeyNavigation.tab: exclusionsField
                            KeyNavigation.backtab: seedField
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: "Exclusiones (separadas por coma)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        TextField {
                            id: exclusionsField; width: parent.width
                            objectName: "exclusionsField"
                            Accessible.name: "Exclusiones separadas por coma"
                            placeholderText: "artista1, artista2, género1"
                            onTextChanged: {
                                root._exclusions = text.split(",").map(function(x) { return x.trim() }).filter(function(x) { return x !== "" })
                            }
                            activeFocusOnTab: true
                            KeyNavigation.tab: qualityCombo
                            KeyNavigation.backtab: seedArtistField
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.md; width: parent.width * 0.48

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Duración (min)"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: durationSpin; width: parent.width; from: 5; to: 480; stepSize: 5; value: root._durationMinutes
                                objectName: "durationSpin"
                                Accessible.name: "Duración del mix en minutos"
                                onValueChanged: root._durationMinutes = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: trackLimitSpin
                                KeyNavigation.backtab: exclusionsField
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Límite pistas"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: trackLimitSpin; width: parent.width; from: 5; to: 200; value: root._trackLimit
                                objectName: "trackLimitSpin"
                                Accessible.name: "Límite máximo de pistas"
                                onValueChanged: root._trackLimit = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: qualityCombo
                                KeyNavigation.backtab: durationSpin
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Variedad"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                Slider {
                                    id: varietySlider; width: 120; from: 0; to: 100; value: root._variety
                                    objectName: "varietySlider"
                                    Accessible.name: "Variedad del mix"
                                    onValueChanged: root._variety = value
                                    activeFocusOnTab: true
                                    KeyNavigation.tab: familiaritySlider
                                    KeyNavigation.backtab: trackLimitSpin
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._variety; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Familiaridad"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                Slider {
                                    id: familiaritySlider; width: 120; from: 0; to: 100; value: root._familiarity
                                    objectName: "familiaritySlider"
                                    Accessible.name: "Familiaridad del mix"
                                    onValueChanged: root._familiarity = value
                                    activeFocusOnTab: true
                                    KeyNavigation.tab: avoidRecentCheck
                                    KeyNavigation.backtab: varietySlider
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._familiarity; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Calidad mínima"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            ComboBox {
                                id: qualityCombo; width: parent.width
                                objectName: "qualityCombo"
                                Accessible.name: "Filtro de calidad mínima"
                                model: [
                                    { text: "Cualquiera", value: "" },
                                    { text: ">= 192 kbps", value: "192" },
                                    { text: ">= 320 kbps", value: "320" },
                                    { text: "Lossless (FLAC)", value: "lossless" }
                                ]
                                textRole: "text"; valueRole: "value"
                                currentIndex: 0
                                onCurrentValueChanged: root._qualityFilter = currentValue
                                activeFocusOnTab: true
                                KeyNavigation.tab: genreCombo
                                KeyNavigation.backtab: familiaritySlider
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Género"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            ComboBox {
                                id: genreCombo; width: parent.width
                                objectName: "genreCombo"
                                Accessible.name: "Filtro de género"
                                model: [
                                    { text: "Cualquiera", value: "" },
                                    { text: "Rock", value: "rock" },
                                    { text: "Pop", value: "pop" },
                                    { text: "Jazz", value: "jazz" },
                                    { text: "Clásica", value: "classical" },
                                    { text: "Electrónica", value: "electronic" },
                                    { text: "Hip Hop", value: "hip hop" },
                                    { text: "R&B", value: "rnb" },
                                    { text: "Metal", value: "metal" },
                                    { text: "Folk", value: "folk" },
                                    { text: "Blues", value: "blues" },
                                    { text: "Country", value: "country" },
                                    { text: "Latina", value: "latin" },
                                    { text: "Reggae", value: "reggae" }
                                ]
                                textRole: "text"; valueRole: "value"
                                currentIndex: 0
                                onCurrentValueChanged: root._genreFilter = currentValue
                                activeFocusOnTab: true
                                KeyNavigation.tab: yearFromSpin
                                KeyNavigation.backtab: qualityCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Año desde"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: yearFromSpin; width: parent.width; from: 1900; to: 2030; value: root._yearFrom
                                objectName: "yearFromSpin"
                                Accessible.name: "Año inicial del filtro"
                                onValueChanged: root._yearFrom = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: yearToSpin
                                KeyNavigation.backtab: genreCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: "Año hasta"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            SpinBox {
                                id: yearToSpin; width: parent.width; from: 1900; to: 2030; value: root._yearTo
                                objectName: "yearToSpin"
                                Accessible.name: "Año final del filtro"
                                onValueChanged: root._yearTo = value
                                activeFocusOnTab: true
                                KeyNavigation.tab: avoidRecentCheck
                                KeyNavigation.backtab: yearFromSpin
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    CheckBox {
                        id: avoidRecentCheck
                        text: "Evitar escuchadas recientemente"
                        checked: root._avoidRecent
                        objectName: "avoidRecentCheck"
                        Accessible.name: "Evitar canciones escuchadas recientemente"
                        onCheckedChanged: root._avoidRecent = checked
                        activeFocusOnTab: true
                        KeyNavigation.tab: generateBtn
                        KeyNavigation.backtab: yearToSpin
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md; width: parent.width

                MichiButton {
                    id: generateBtn
                    text: {
                        if (root._state === "VALIDATING") return "Validando..."
                        if (root._state === "GENERATING") return "Generando..."
                        if (root._state === "CANCELLING") return "Cancelando..."
                        if (root._state === "CANCELLED") return "Regenerar"
                        if (root._state === "NO_CANDIDATES") return "Reintentar"
                        if (root._state === "FAILED") return "Reintentar"
                        return "Generar Mix"
                    }
                    variant: root._state === "FAILED" ? "danger" : "primary"
                    objectName: "generateBtn"
                    Accessible.name: text
                    activeFocusOnTab: true
                    enabled: root._state !== "VALIDATING" && root._state !== "GENERATING" && root._state !== "CANCELLING"
                    KeyNavigation.tab: cancelBtn
                    KeyNavigation.backtab: avoidRecentCheck

                    onClicked: {
                        if (root._state === "CANCELLED" || root._state === "NO_CANDIDATES") {
                            root.retry()
                        } else {
                            root.generate()
                        }
                    }
                }

                MichiButton {
                    id: cancelBtn
                    text: "Cancelar"
                    variant: "danger"
                    objectName: "cancelBtn"
                    Accessible.name: "Cancelar generación"
                    activeFocusOnTab: true
                    visible: root._state === "GENERATING"
                    KeyNavigation.tab: resultList
                    KeyNavigation.backtab: generateBtn

                    onClicked: root.cancelGeneration()
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "GENERATING" || root._state === "CANCELLING" || root._state === "CANCELLED"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: root._statusMessage; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        MichiProgressBar {
                            width: parent.width
                            from: 0; to: root._progressTotal > 0 ? root._progressTotal : 100
                            value: root._progressCurrent
                            indeterminate: root._state === "GENERATING" && root._progressTotal === 0
                            accessibleName: "Progreso de generación"
                        }

                        Text {
                            text: root._progressTotal > 0
                                ? root._progressCurrent + " / " + root._progressTotal + " canciones"
                                : "Buscando canciones..."
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "NO_CANDIDATES"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: "No se encontraron candidatos"; color: MichiTheme.colors.warning
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: "Prueba con una selección diferente o ajusta los filtros."
                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap; width: parent.width
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "CANCELLED"

                GlassMaterial {
                    width: parent.width; radius: MichiTheme.radiusMd; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Generación cancelada"; color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: "Puedes ajustar los parámetros y generar de nuevo."
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "READY"

                SectionHeader {
                    text: "Mix generado — " + root._resultSongs.length + " canciones"
                    width: parent.width
                }

                ListView {
                    id: resultList
                    width: parent.width; height: Math.min(360, root._resultSongs.length * 48)
                    model: root._resultSongs; clip: true; spacing: 2
                    activeFocusOnTab: true
                    objectName: "generatedSongsList"
                    Accessible.name: "Canciones generadas"

                    delegate: Rectangle {
                        width: parent.width; height: 44
                        color: modelData._hovered ? MichiTheme.colors.surfaceHover : "transparent"
                        radius: MichiTheme.radiusSm
                        activeFocusOnTab: true
                        objectName: "generatedSongItem_" + index
                        Accessible.name: modelData.title + " - " + modelData.artist
                        KeyNavigation.tab: index < root._resultSongs.length - 1
                            ? resultList.itemAtIndex(index + 1)
                            : showResultsBtn
                        KeyNavigation.backtab: index > 0
                            ? resultList.itemAtIndex(index - 1)
                            : cancelBtn

                        Keys.onReturnPressed: onClick()
                        Keys.onSpacePressed: onClick()

                        property bool _hovered: false

                        signal onClick()

                        Row {
                            anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                            Text {
                                width: parent.width * 0.35; text: modelData.title || ""
                                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: parent.width * 0.25; text: modelData.artist || ""
                                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: parent.width * 0.20; text: modelData.album || ""
                                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                width: 24; text: "P"; color: MichiTheme.colors.accentBlue
                                font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.mx && typeof root.mx.playFromIndex === "function")
                                            root.mx.playFromIndex(index)
                                    }
                                }
                            }

                            Text {
                                width: 24; text: "+"; color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.cardTitleSize; anchors.verticalCenter: parent.verticalCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.mx && typeof root.mx.enqueueTrack === "function")
                                            root.mx.enqueueTrack(index)
                                    }
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true
                            onEntered: modelData._hovered = true
                            onExited: modelData._hovered = false
                        }
                    }

                    Text {
                        anchors.centerIn: parent; visible: parent.count === 0
                        text: "No hay canciones generadas"
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    }
                }

                Row {
                    id: resultActionsRow
                    spacing: MichiTheme.spacing.sm; width: parent.width

                    MichiButton {
                        id: showResultsBtn
                        text: "Ver resultados completos"; variant: "primary"
                        objectName: "showResultsBtn"
                        Accessible.name: "Ver resultados completos del mix"
                        activeFocusOnTab: true
                        KeyNavigation.tab: regenerateFromResultBtn
                        KeyNavigation.backtab: resultList
                        onClicked: root.showResults(root._resultSongs, root._mixType)
                    }

                    MichiButton {
                        id: regenerateFromResultBtn
                        text: "Regenerar"; variant: "ghost"
                        objectName: "regenerateFromResultBtn"
                        Accessible.name: "Regenerar mix"
                        activeFocusOnTab: true
                        KeyNavigation.tab: showResultsBtn
                        KeyNavigation.backtab: showResultsBtn
                        onClicked: root.retry()
                    }
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: "Bridge no disponible — funcionalidad limitada"
                kind: "disconnected"
            }
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        }
    }
}
