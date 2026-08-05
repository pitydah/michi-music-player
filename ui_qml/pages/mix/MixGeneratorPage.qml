import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Mix Generator")
    objectName: "mixGeneratorPage"
    focus: true
    id: root

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

    signal backRequested()
    signal showResults(var songs, string mixType)

    MichiResponsive { id: responsive; availableWidth: root.width }

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
        root._statusMessage = qsTr("Validando configuración...")

        if (!root.mx) {
            root._state = "FAILED"
            root._errorMessage = qsTr("Servicio de mix no disponible")
            return false
        }

        if (root._mixType === "custom" && root._seedValue === "" && root._seedArtist === "") {
            root._state = "FAILED"
            root._errorMessage = qsTr("Selecciona un artista o introduce parámetros para el mix personalizado")
            return false
        }

        return true
    }

    function generate() {
        if (!validate()) return
        root._state = "GENERATING"
        root._statusMessage = qsTr("Generando mix...")
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
                    root._statusMessage = qsTr("Mix generado: %1 canciones").arg(root._resultSongs.length)
                } else {
                    root._state = "NO_CANDIDATES"
                    root._statusMessage = ""
                }
            } else {
                root._state = "FAILED"
                root._errorMessage = (result && result.error) || qsTr("Error al generar el mix")
            }
        } else {
            root._state = "FAILED"
            root._errorMessage = qsTr("Bridge no disponible")
        }
    }

    function cancelGeneration() {
        if (root._state !== "GENERATING") return
        root._state = "CANCELLING"
        root._statusMessage = qsTr("Cancelando generación...")

        if (root.mx && typeof root.mx.cancelGeneration === "function") {
            root.mx.cancelGeneration()
        }
        root._state = "CANCELLED"
        root._statusMessage = qsTr("Generación cancelada")
        root._resultSongs = []
    }

    function retry() {
        root.reset()
        root.generate()
    }

    function _yearFromText() {
        return root._yearFrom > 0 ? String(root._yearFrom) : ""
    }

    function _yearToText() {
        return root._yearTo > 0 ? String(root._yearTo) : ""
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
                    id: generatorBackBtn
                    text: qsTr("Volver"); variant: "ghost"
                    activeFocusOnTab: true
                    onClicked: {
                        root.backRequested()
                        if (typeof navigationBridge !== "undefined" && navigationBridge)
                            navigationBridge.back()
                    }
                    KeyNavigation.tab: mixTypeCombo
                }

                Text {
                    text: qsTr("Generar Mix"); color: MichiTheme.colors.textPrimary
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

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Column {
                    spacing: MichiTheme.spacing.md
                    width: responsive.compact ? parent.width : (parent.width - MichiTheme.spacing.lg) / 2

                    Column { spacing: MichiTheme.spacing.sm; width: parent.width
                        Text { text: qsTr("Tipo de Mix"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium }

                        MichiComboBox {
                            id: mixTypeCombo; width: parent.width
                            textRole: "text"
                            accessibleName: qsTr("Tipo de Mix")
                            model: [
                                { text: qsTr("Mix diario"), value: "daily_mix" },
                                { text: qsTr("Favoritos"), value: "favorites" },
                                { text: qsTr("Recientes"), value: "recent" },
                                { text: qsTr("No escuchadas"), value: "unplayed" },
                                { text: qsTr("Más escuchadas"), value: "most_played" },
                                { text: qsTr("Por artista"), value: "by_artist" },
                                { text: qsTr("Por álbum"), value: "by_album" },
                                { text: qsTr("Por género"), value: "by_genre" },
                                { text: qsTr("Por década"), value: "by_decade" },
                                { text: qsTr("Por año"), value: "by_year" },
                                { text: qsTr("Alta calidad"), value: "high_quality" },
                                { text: qsTr("Redescubrimiento"), value: "rediscovery" },
                                { text: qsTr("Personalizado"), value: "custom" }
                            ]
                            currentIndex: 0
                            onActivated: function(index) { root._mixType = model[index].value }
                            KeyNavigation.tab: seedField
                            KeyNavigation.backtab: generatorBackBtn
                            enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                        }
                    }

                    MichiTextField {
                        id: seedField; width: parent.width
                        label: qsTr("Seed (opcional)")
                        placeholderText: qsTr('Parámetros en JSON (ej: {"artist":"Genesis"})')
                        text: root._seedValue
                        onTextEdited: function(newText) { root._seedValue = newText }
                        KeyNavigation.tab: seedArtistField
                        KeyNavigation.backtab: mixTypeCombo
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }

                    MichiTextField {
                        id: seedArtistField; width: parent.width
                        label: qsTr("Artista semilla")
                        placeholderText: qsTr("Nombre del artista")
                        text: root._seedArtist
                        onTextEdited: function(newText) { root._seedArtist = newText }
                        KeyNavigation.tab: exclusionsField
                        KeyNavigation.backtab: seedField
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }

                    MichiTextField {
                        id: exclusionsField; width: parent.width
                        label: qsTr("Exclusiones (separadas por coma)")
                        placeholderText: qsTr("artista1, artista2, género1")
                        onTextEdited: function(newText) {
                            root._exclusions = newText.split(",").map(function(x) { return x.trim() }).filter(function(x) { return x !== "" })
                        }
                        KeyNavigation.tab: durationSpin
                        KeyNavigation.backtab: seedArtistField
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.md
                    width: responsive.compact ? parent.width : (parent.width - MichiTheme.spacing.lg) / 2

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Duración (min)"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            MichiDoubleSpinBox {
                                id: durationSpin; width: parent.width
                                from: 5; to: 480; stepSize: 5; decimals: 0
                                value: root._durationMinutes
                                accessibleName: qsTr("Duración en minutos")
                                onValueModified: root._durationMinutes = Math.round(value)
                                KeyNavigation.tab: trackLimitSpin
                                KeyNavigation.backtab: exclusionsField
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Límite pistas"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            MichiDoubleSpinBox {
                                id: trackLimitSpin; width: parent.width
                                from: 5; to: 200; stepSize: 1; decimals: 0
                                value: root._trackLimit
                                accessibleName: qsTr("Límite de pistas")
                                onValueModified: root._trackLimit = Math.round(value)
                                KeyNavigation.tab: varietySlider
                                KeyNavigation.backtab: durationSpin
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Variedad"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                MichiSlider {
                                    id: varietySlider; width: 120
                                    from: 0; to: 100; stepSize: 1
                                    value: root._variety
                                    accessibleName: qsTr("Variedad")
                                    onMoved: function(value) { root._variety = Math.round(value) }
                                    KeyNavigation.tab: familiaritySlider
                                    KeyNavigation.backtab: trackLimitSpin
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._variety; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Familiaridad"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            Row { spacing: MichiTheme.spacing.sm
                                MichiSlider {
                                    id: familiaritySlider; width: 120
                                    from: 0; to: 100; stepSize: 1
                                    value: root._familiarity
                                    accessibleName: qsTr("Familiaridad")
                                    onMoved: function(value) { root._familiarity = Math.round(value) }
                                    KeyNavigation.tab: qualityCombo
                                    KeyNavigation.backtab: varietySlider
                                    enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                                }
                                Text { text: root._familiarity; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Calidad mínima"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            MichiComboBox {
                                id: qualityCombo; width: parent.width
                                textRole: "text"
                                accessibleName: qsTr("Calidad mínima")
                                model: [
                                    { text: qsTr("Cualquiera"), value: "" },
                                    { text: qsTr(">= 192 kbps"), value: "192" },
                                    { text: qsTr(">= 320 kbps"), value: "320" },
                                    { text: qsTr("Lossless (FLAC)"), value: "lossless" }
                                ]
                                currentIndex: 0
                                onActivated: function(index) { root._qualityFilter = model[index].value }
                                KeyNavigation.tab: genreCombo
                                KeyNavigation.backtab: familiaritySlider
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            Text { text: qsTr("Género"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

                            MichiComboBox {
                                id: genreCombo; width: parent.width
                                textRole: "text"
                                accessibleName: qsTr("Género")
                                model: [
                                    { text: qsTr("Cualquiera"), value: "" },
                                    { text: qsTr("Rock"), value: "rock" },
                                    { text: qsTr("Pop"), value: "pop" },
                                    { text: qsTr("Jazz"), value: "jazz" },
                                    { text: qsTr("Clásica"), value: "classical" },
                                    { text: qsTr("Electrónica"), value: "electronic" },
                                    { text: qsTr("Hip Hop"), value: "hip hop" },
                                    { text: qsTr("R&B"), value: "rnb" },
                                    { text: qsTr("Metal"), value: "metal" },
                                    { text: qsTr("Folk"), value: "folk" },
                                    { text: qsTr("Blues"), value: "blues" },
                                    { text: qsTr("Country"), value: "country" },
                                    { text: qsTr("Latina"), value: "latin" },
                                    { text: qsTr("Reggae"), value: "reggae" }
                                ]
                                currentIndex: 0
                                onActivated: function(index) { root._genreFilter = model[index].value }
                                KeyNavigation.tab: yearFromField
                                KeyNavigation.backtab: qualityCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    Row { spacing: MichiTheme.spacing.md; width: parent.width
                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            MichiTextField {
                                id: yearFromField; width: parent.width
                                label: qsTr("Año desde")
                                placeholderText: qsTr("1970")
                                text: root._yearFromText()
                                onTextEdited: function(newText) {
                                    var v = parseInt(newText)
                                    root._yearFrom = isNaN(v) ? 0 : Math.max(0, Math.min(2030, v))
                                }
                                KeyNavigation.tab: yearToField
                                KeyNavigation.backtab: genreCombo
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width * 0.45
                            MichiTextField {
                                id: yearToField; width: parent.width
                                label: qsTr("Año hasta")
                                placeholderText: qsTr("2026")
                                text: root._yearToText()
                                onTextEdited: function(newText) {
                                    var v = parseInt(newText)
                                    root._yearTo = isNaN(v) ? 0 : Math.max(0, Math.min(2030, v))
                                }
                                KeyNavigation.tab: avoidRecentCheck
                                KeyNavigation.backtab: yearFromField
                                enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                            }
                        }
                    }

                    MichiCheckBox {
                        id: avoidRecentCheck
                        text: qsTr("Evitar escuchadas recientemente")
                        checked: root._avoidRecent
                        onToggled: function(checked) { root._avoidRecent = checked }
                        KeyNavigation.tab: generateBtn
                        KeyNavigation.backtab: yearToField
                        enabled: root._state !== "GENERATING" && root._state !== "CANCELLING"
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md; width: parent.width

                MichiButton {
                    id: generateBtn
                    text: {
                        if (root._state === "VALIDATING") return qsTr("Validando...")
                        if (root._state === "GENERATING") return qsTr("Generando...")
                        if (root._state === "CANCELLING") return qsTr("Cancelando...")
                        if (root._state === "CANCELLED") return qsTr("Regenerar")
                        if (root._state === "NO_CANDIDATES") return qsTr("Reintentar")
                        if (root._state === "FAILED") return qsTr("Reintentar")
                        return qsTr("Generar Mix")
                    }
                    variant: root._state === "FAILED" ? "danger" : "primary"
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
                    text: qsTr("Cancelar")
                    variant: "danger"
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
                    width: parent.width; radius: MichiTheme.radius.md; variant: "subtle"

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
                            accessibleName: qsTr("Progreso de generación")
                        }

                        Text {
                            text: root._progressTotal > 0
                                ? qsTr("%1 / %2 canciones").arg(root._progressCurrent).arg(root._progressTotal)
                                : qsTr("Buscando canciones...")
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
                    width: parent.width; radius: MichiTheme.radius.md; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("No se encontraron candidatos"); color: MichiTheme.colors.warning
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: qsTr("Prueba con una selección diferente o ajusta los filtros.")
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
                    width: parent.width; radius: MichiTheme.radius.md; variant: "subtle"

                    Column {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                        Text {
                            text: qsTr("Generación cancelada"); color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium
                        }

                        Text {
                            text: qsTr("Puedes ajustar los parámetros y generar de nuevo.")
                            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                        }
                    }
                }
            }

            Column {
                width: parent.width; spacing: MichiTheme.spacing.md
                visible: root._state === "READY"

                SectionHeader {
                    text: qsTr("Mix generado — %1 canciones").arg(root._resultSongs.length)
                    width: parent.width
                }

                ListView {
                    focusPolicy: Qt.StrongFocus
                    Accessible.role: Accessible.List
                    Accessible.name: qsTr("Canciones generadas")
                    id: resultList
                    width: parent.width; height: Math.min(360, root._resultSongs.length * 48)
                    model: root._resultSongs; clip: true; spacing: 2
                    activeFocusOnTab: true

                    delegate: Rectangle {
                        width: parent.width; height: 44
                        color: resultRowHover.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                        radius: MichiTheme.radius.sm
                        activeFocusOnTab: true
                        KeyNavigation.tab: index < root._resultSongs.length - 1
                            ? resultList.itemAtIndex(index + 1)
                            : showResultsBtn
                        KeyNavigation.backtab: index > 0
                            ? resultList.itemAtIndex(index - 1)
                            : cancelBtn

                        Keys.onReturnPressed: {
                            if (root.mx && typeof root.mx.playFromIndex === "function")
                                root.mx.playFromIndex(index)
                        }
                        Keys.onSpacePressed: {
                            if (root.mx && typeof root.mx.playFromIndex === "function")
                                root.mx.playFromIndex(index)
                        }

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

                            MichiIcon {
                                width: 24; height: 24
                                source: "../../../icons/sidebar/play.svg"
                                color: MichiTheme.colors.accentBlue
                                anchors.verticalCenter: parent.verticalCenter
                                accessibleName: qsTr("Reproducir")
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.mx && typeof root.mx.playFromIndex === "function")
                                            root.mx.playFromIndex(index)
                                    }
                                }
                            }

                            MichiIcon {
                                width: 24; height: 24
                                source: "../../../icons/actions/plus.svg"
                                color: MichiTheme.colors.textMuted
                                anchors.verticalCenter: parent.verticalCenter
                                accessibleName: qsTr("Agregar a cola")
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
                            id: resultRowHover
                            anchors.fill: parent; hoverEnabled: true
                            acceptedButtons: Qt.NoButton
                        }
                    }

                    Text {
                        anchors.centerIn: parent; visible: parent.count === 0
                        text: qsTr("No hay canciones generadas")
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                    }
                }

                Row {
                    id: resultActionsRow
                    spacing: MichiTheme.spacing.sm; width: parent.width

                    MichiButton {
                        id: showResultsBtn
                        text: qsTr("Ver resultados completos"); variant: "primary"
                        activeFocusOnTab: true
                        KeyNavigation.tab: regenerateFromResultBtn
                        KeyNavigation.backtab: resultList
                        onClicked: {
                            root.showResults(root._resultSongs, root._mixType)
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix.result")
                        }
                    }

                    MichiButton {
                        id: regenerateFromResultBtn
                        text: qsTr("Regenerar"); variant: "ghost"
                        activeFocusOnTab: true
                        KeyNavigation.tab: showResultsBtn
                        KeyNavigation.backtab: showResultsBtn
                        onClicked: root.retry()
                    }
                }
            }

            StatusBadge {
                visible: root.mx === null
                text: qsTr("Bridge no disponible — funcionalidad limitada")
                kind: "disconnected"
            }
        }
    }
}
