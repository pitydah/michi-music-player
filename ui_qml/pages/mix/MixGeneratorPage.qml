import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "mixGenerator.page"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null

    property string state: "IDLE"
    property string mixType: ""
    property string seed: ""
    property string exclusions: ""
    property int targetDuration: 30
    property int targetLimit: 25
    property int variety: 50
    property int familiarity: 50
    property int progressCurrent: 0
    property int progressTotal: 100
    property string _errorMsg: ""

    signal backClicked()
    signal generationComplete(var result)

    Accessible.role: Accessible.Pane
    Accessible.name: "Generador de Mix"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "mixGenerator.focusScope"

        Keys.onEscapePressed: {
            if (root.state === "GENERATING" || root.state === "CANCELLING") {
                root._cancelGeneration()
            } else {
                root.backClicked()
            }
        }

        Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            focus: true
            objectName: "mixGenerator.flickable"

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                Row {
                    spacing: MichiTheme.spacing.sm
                    width: parent.width

                    MichiButton {
                        text: "< Volver"
                        variant: "ghost"
                        onClicked: root.backClicked()
                        objectName: "mixGenerator.backButton"
                        Accessible.name: "Volver"
                        KeyNavigation.tab: mixTypeCombo
                    }

                    Text {
                        text: "Generar Mix"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.pageTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        anchors.verticalCenter: parent.verticalCenter
                        Accessible.role: Accessible.Heading
                        Accessible.name: "Generar Mix"
                    }
                }

                GlassMaterial {
                    width: parent.width
                    implicitHeight: configColumn.height + MichiTheme.spacing.xl * 2
                    radius: MichiTheme.radiusMd
                    variant: root.state === "GENERATING" ? "accent" : "elevated"
                    objectName: "mixGenerator.panel"

                    Column {
                        id: configColumn
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Configuración del mix"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightSemiBold
                        }

                        Text {
                            text: "Estado: " + root.state
                            color: root.state === "FAILED" || root.state === "NO_CANDIDATES"
                                ? MichiTheme.colors.error
                                : (root.state === "READY" ? MichiTheme.colors.success : MichiTheme.colors.textMuted)
                            font.pixelSize: MichiTheme.typography.metaSize
                            visible: root.state !== "IDLE"
                        }

                        Row {
                            spacing: MichiTheme.spacing.md
                            width: parent.width

                            Column {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width * 0.48

                                Text {
                                    text: "Tipo de mix"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }

                                ComboBox {
                                    id: mixTypeCombo
                                    width: parent.width
                                    model: ["favorites", "recent", "most_played", "unplayed", "rediscovery", "daily_mix", "by_artist", "by_genre", "by_decade", "high_quality"]
                                    currentIndex: 0
                                    enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                                    objectName: "mixGenerator.mixType"
                                    Accessible.name: "Tipo de mix"
                                    onCurrentTextChanged: root.mixType = currentText
                                    KeyNavigation.tab: seedField
                                }
                            }

                            Column {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width * 0.48

                                Text {
                                    text: "Seed (opcional)"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }

                                TextField {
                                    id: seedField
                                    width: parent.width
                                    placeholderText: "Deterministic seed"
                                    enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                                    objectName: "mixGenerator.seedField"
                                    Accessible.name: "Seed determinista"
                                    onTextChanged: root.seed = text
                                    KeyNavigation.tab: durationSpin
                                }
                            }
                        }

                        Row {
                            spacing: MichiTheme.spacing.md
                            width: parent.width

                            Column {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width * 0.30

                                Text {
                                    text: "Duración (min)"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }

                                SpinBox {
                                    id: durationSpin
                                    from: 5; to: 480; value: root.targetDuration
                                    enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                                    onValueChanged: root.targetDuration = value
                                    objectName: "mixGenerator.durationSpin"
                                    Accessible.name: "Duración en minutos"
                                    KeyNavigation.tab: limitSpin
                                }
                            }

                            Column {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width * 0.30

                                Text {
                                    text: "Límite canciones"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }

                                SpinBox {
                                    id: limitSpin
                                    from: 5; to: 200; value: root.targetLimit
                                    enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                                    onValueChanged: root.targetLimit = value
                                    objectName: "mixGenerator.limitSpin"
                                    Accessible.name: "Límite de canciones"
                                    KeyNavigation.tab: varietySlider
                                }
                            }

                            Column {
                                spacing: MichiTheme.spacing.sm
                                width: parent.width * 0.30

                                Text {
                                    text: "Exclusiones"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }

                                TextField {
                                    width: parent.width
                                    placeholderText: "artist, genre, ..."
                                    enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                                    onTextChanged: root.exclusions = text
                                    objectName: "mixGenerator.exclusionsField"
                                    Accessible.name: "Exclusiones"
                                    KeyNavigation.tab: familiaritySlider
                                }
                            }
                        }

                        Text {
                            text: "Variedad: " + root.variety + "%"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        MichiSlider {
                            id: varietySlider
                            width: parent.width
                            from: 0; to: 100
                            value: root.variety
                            enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                            accessibleName: "Variedad del mix"
                            onMoved: root.variety = value
                            KeyNavigation.tab: familiaritySlider
                        }

                        Text {
                            text: "Familiaridad: " + root.familiarity + "%"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        MichiSlider {
                            id: familiaritySlider
                            width: parent.width
                            from: 0; to: 100
                            value: root.familiarity
                            enabled: root.state !== "GENERATING" && root.state !== "CANCELLING"
                            accessibleName: "Familiaridad del mix"
                            onMoved: root.familiarity = value
                            KeyNavigation.tab: actionRow
                        }
                    }
                }

                MixGenerationProgress {
                    visible: root.state === "GENERATING"
                    progress: root.progressCurrent
                    total: root.progressTotal
                    statusText: "Generando mix..."
                    cancellable: true
                    onCancelRequested: root._cancelGeneration()
                }

                Text {
                    text: root._errorMsg
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.bodySize
                    visible: root._errorMsg !== ""
                    wrapMode: Text.WordWrap
                    width: parent.width
                    Accessible.role: Accessible.Alert
                    Accessible.name: root._errorMsg
                }

                Row {
                    id: actionRow
                    spacing: MichiTheme.spacing.sm

                    MichiButton {
                        text: {
                            if (root.state === "VALIDATING") return "Validando..."
                            if (root.state === "GENERATING") return "Generando..."
                            if (root.state === "CANCELLING") return "Cancelando..."
                            if (root.state === "CANCELLED") return "Regenerar"
                            if (root.state === "READY") return "Regenerar"
                            if (root.state === "FAILED") return "Reintentar"
                            return "Generar"
                        }
                        variant: "primary"
                        enabled: root.state !== "GENERATING" && root.state !== "CANCELLING" && root.state !== "VALIDATING"
                        onClicked: root._startGeneration()
                        objectName: "mixGenerator.generateButton"
                        Accessible.name: "Generar mix"
                        KeyNavigation.tab: cancelBtn
                    }

                    MichiButton {
                        id: cancelBtn
                        text: "Cancelar"
                        variant: "danger"
                        visible: root.state === "GENERATING" || root.state === "VALIDATING"
                        onClicked: root._cancelGeneration()
                        objectName: "mixGenerator.cancelButton"
                        Accessible.name: "Cancelar generación"
                        KeyNavigation.tab: backButton
                    }

                    MichiButton {
                        text: "Ver resultado"
                        variant: "secondary"
                        visible: root.state === "READY" || root.state === "CANCELLED"
                        enabled: root.state === "READY"
                        onClicked: {
                            if (typeof navigationBridge !== "undefined" && navigationBridge)
                                navigationBridge.navigate("mix_result")
                        }
                        objectName: "mixGenerator.viewResultButton"
                        Accessible.name: "Ver resultado del mix"
                        KeyNavigation.tab: backButton
                    }
                }

                StatusBadge {
                    text: {
                        if (root.state === "NO_CANDIDATES") return "No se encontraron candidatos"
                        if (root.state === "FAILED") return "Error en la generación"
                        if (root.state === "CANCELLED") return "Generación cancelada"
                        if (root.state === "READY") return "Mix generado correctamente"
                        return ""
                    }
                    kind: {
                        if (root.state === "NO_CANDIDATES") return "warning"
                        if (root.state === "FAILED") return "error"
                        if (root.state === "CANCELLED") return "disconnected"
                        if (root.state === "READY") return "success"
                        return "info"
                    }
                    visible: ["NO_CANDIDATES", "FAILED", "CANCELLED", "READY"].indexOf(root.state) >= 0
                }
            }
        }
    }

    function _startGeneration() {
        if (!root.mx) {
            root._errorMsg = "Bridge no disponible"
            return
        }
        root.state = "VALIDATING"
        root._errorMsg = ""

        try {
            var result = root.mx.loadMix(root.mixType || "favorites", root.seed)
            if (result && result.ok) {
                root.state = "READY"
                root.generationComplete(result)
            } else if (result && result.partial) {
                root.state = "READY"
                root._errorMsg = "Resultado parcial: " + (result.count || 0) + " canciones"
                root.generationComplete(result)
            } else {
                root.state = "NO_CANDIDATES"
                root._errorMsg = result && result.error ? result.error : "No se encontraron candidatos"
            }
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
        }
    }
}
