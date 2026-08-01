import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    objectName: "assistantPage"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Michi AI")

    property var ai: typeof michiAiBridge !== "undefined" ? michiAiBridge : null
    property bool _initialized: false
    property string _aiStatus: "idle"

    // The bridge emits uppercase V2 states (IDLE, PLANNING, RUNNING,
    // CONFIRMATION_REQUIRED, SUCCEEDED, ...); map them to the lowercase
    // UI states this page renders.
    function _normalizeStatus(raw) {
        switch ((raw || "").toUpperCase()) {
        case "IDLE": return "idle"
        case "PLANNING": return "planning"
        case "QUEUED": return "queued"
        case "RUNNING": return "executing"
        case "CONFIRMATION_REQUIRED": return "awaiting_confirmation"
        case "CANCELLING": return "cancelling"
        case "CANCELLED": return "cancelled"
        case "SUCCEEDED": return "completed"
        case "PARTIAL_SUCCESS": return "partially_executed"
        case "FAILED": return "failed"
        default: return (raw || "idle").toLowerCase()
        }
    }
    property string _lastError: root.ai ? root.ai.lastError || "" : "No disponible"
    property var _chatHistory: root.ai ? parseChatHistory(root.ai.getChatHistory()) : []
    property string selectedAiModelId: "calico"
    property int pageState: (root.ai && root.ai.backendAvailable) ? stateReady : stateError

    signal aiModelSelectionRequested(string modelId)

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    function parseChatHistory(jsonStr) {
        if (!jsonStr || jsonStr === "") return []
        try {
            return JSON.parse(jsonStr)
        } catch (e) {
            return []
        }
    }

    on_AiStatusChanged: {
        if (root._aiStatus === "executing") {
            root._executing = true
        } else {
            root._executing = false
        }
        if (root._aiStatus === "awaiting_confirmation") {
            var plan = root.ai && root.ai.currentPlan ? root.ai.currentPlan : {}
            actionPreview.actionName = plan.action || qsTr("Acción pendiente")
            actionPreview.actionDescription = (plan.intent ? qsTr("Intención detectada: ") + plan.intent : "")
                + (plan.risk_level ? " · " + qsTr("Riesgo: ") + plan.risk_level : "")
            actionPreview.destructive = plan.risk_level === "critical" || plan.risk_level === "destructive"
            actionPreview.visible = true
        } else {
            actionPreview.visible = false
        }
        if (root._aiStatus === "completed" || root._aiStatus === "failed" || root._aiStatus === "partially_executed") {
            showResultForStatus()
        }
    }

    property bool _executing: false
    property string _pendingConfirmAction: ""

    function _traceText() {
        var t = root.ai && root.ai.lastTrace ? root.ai.lastTrace : {}
        var parts = []
        if (t.intent) parts.push(qsTr("Intención: ") + t.intent)
        if (t.backend) parts.push(qsTr("Backend: ") + t.backend)
        if (t.risk_level) parts.push(qsTr("Riesgo: ") + t.risk_level)
        if (t.elapsed_ms !== undefined && t.elapsed_ms !== "") parts.push(qsTr("Tiempo: ") + t.elapsed_ms + " ms")
        if (t.tool_ok !== undefined && t.tool_ok !== null) parts.push(qsTr("Tool: ") + (t.tool_ok ? "OK" : "error"))
        if (t.error) parts.push(qsTr("Error: ") + t.error)
        return parts.join("\n")
    }

    function showResultForStatus() {
        var trace = root._traceText()
        if (root._aiStatus === "completed") {
            executionResult.status = "success"
            executionResult.summaryText = "Acción ejecutada correctamente."
            executionResult.detailText = trace
            executionResult.visible = true
        } else if (root._aiStatus === "failed") {
            executionResult.status = "failure"
            executionResult.summaryText = "Error al ejecutar la acción."
            executionResult.detailText = root._lastError + (trace !== "" ? "\n" + trace : "")
            executionResult.visible = true
        } else if (root._aiStatus === "partially_executed") {
            executionResult.status = "partial"
            executionResult.summaryText = "Acción ejecutada parcialmente."
            executionResult.detailText = trace
            executionResult.visible = true
        }
    }

    Component.onCompleted: {
        if (root.ai && typeof root.ai.refresh !== "undefined") {
            root.ai.refresh()
        }
        root._initialized = true
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: MichiLoadingState { title: qsTr("Cargando asistente") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState {
            message: root.ai && !root.ai.backendAvailable
                     ? qsTr("Asistente no disponible: el servicio de IA no está conectado. Verifica que Michi AI esté configurado en Ajustes.")
                     : qsTr("Asistente no disponible")
        }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: MichiEmptyState { title: qsTr("Asistente sin datos"); message: "Configura el asistente en Ajustes" }
    }

    Flickable {
        visible: root.pageState === root.stateReady
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            HeroMaterial {
                id: aiHero
                width: parent.width
                height: 140
                radius: MichiTheme.radius.lg
                showGlow: root.ai !== null

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.sm

                    Row {
                        spacing: MichiTheme.spacing.md
                        width: parent.width

                        Text {
                            text: "Michi AI"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.heroTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        StatusBadge {
                            text: root.ai ? (root._aiStatus === "idle" ? "Listo" : root._aiStatus) : qsTr("No disponible")
                            kind: root.ai ? (root._aiStatus === "idle" || root._aiStatus === "completed" ? "success" : root._aiStatus === "failed" || root._aiStatus === "unavailable" ? "error" : root._aiStatus === "executing" ? "active" : "info") : "disconnected"
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        StatusBadge {
                            text: qsTr("Experimental")
                            kind: "experimental"
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Text {
                        text: root.ai === null
                            ? "Asistente no disponible. Verifica la conexión con los servicios de Michi."
                            : root._aiStatus === "initializing"
                                ? "Inicializando asistente..."
                                : root._aiStatus === "loading"
                                    ? "Cargando modelos y servicios..."
                                    : root._aiStatus === "error"
                                        ? "Error: " + root._lastError
                                        : root._aiStatus === "unavailable"
                                            ? "Asistente no disponible en este contexto."
                                            : "Asistente inteligente para tu ecosistema musical. Pregunta, explora y descubre."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.70
                        wrapMode: Text.WordWrap
                    }
                }
            }

            AIModelSelector {
                id: aiModelSelector
                width: parent.width
                selectedModelId: root.selectedAiModelId
                integrationReady: root.ai && root.ai.backendAvailable
                backendAvailable: root.ai && root.ai.backendAvailable
                onModelSelectionRequested: function(modelId) {
                    root.selectedAiModelId = modelId
                    root.aiModelSelectionRequested(modelId)
                }
            }

            SectionHeader {
                id: capabilitiesHeader
                text: qsTr("Capacidades disponibles")
                width: parent.width
                visible: capabilitiesRepeater.count > 0
            }

            Flow {
                id: capabilitiesFlow
                width: parent.width
                spacing: MichiTheme.spacing.sm
                visible: capabilitiesRepeater.count > 0

                Repeater {
                    id: capabilitiesRepeater
                    model: root.ai && root.ai.capabilities ? root.ai.capabilities : []

                    StatusBadge {
                        text: modelData.available
                              ? modelData.area + " · " + modelData.tool_count
                              : qsTr("Limitado: ") + (modelData.detail || modelData.area)
                        kind: modelData.available ? "info" : "warning"
                    }
                }
            }

            SectionHeader {
                id: suggestionsHeader
                text: qsTr("Sugerencias")
                width: parent.width
            }

            Repeater {
                id: suggestionsRepeater
                model: ListModel {}

                SuggestionCard {
                    width: parent.width
                    suggestionTitle: model.title || ""
                    suggestionDescription: model.description || ""
                    actionRoute: model.route || ""
                    activeFocusOnTab: true
                    Keys.onReturnPressed: onActionTriggered()
                    Keys.onSpacePressed: onActionTriggered()
                    onActionTriggered: {
                        if (model.action && root.ai && typeof root.ai.sendMessage !== "undefined") {
                            root.ai.sendMessage(model.action)
                        } else if (model.route && typeof navigationBridge !== "undefined" && navigationBridge) {
                            navigationBridge.navigate(model.route)
                        }
                    }
                }
            }

            AssistantConversation {
                id: conversation
                width: parent.width
                chatHistory: root._chatHistory
                aiThinking: root._aiStatus === "understanding" || root._aiStatus === "planning"
            }

            AssistantActionPreview {
                id: actionPreview
                width: parent.width
                visible: false

                onConfirm: {
                    if (root.ai) {
                        var plan = root.ai.currentPlan || {}
                        if (plan.plan_id && typeof root.ai.confirmPlan !== "undefined")
                            root.ai.confirmPlan(plan.plan_id)
                        else if (typeof root.ai.sendMessage !== "undefined")
                            root.ai.sendMessage("sí")
                    }
                    actionPreview.visible = false
                }

                onReject: {
                    if (root.ai) {
                        var plan = root.ai.currentPlan || {}
                        if (plan.plan_id && typeof root.ai.rejectPlan !== "undefined")
                            root.ai.rejectPlan(plan.plan_id)
                        else if (typeof root.ai.sendMessage !== "undefined")
                            root.ai.sendMessage("no")
                    }
                    actionPreview.visible = false
                }
            }

            AssistantExecutionResult {
                id: executionResult
                width: parent.width
                visible: false

                onRetry: {
                    executionResult.visible = false
                    if (root.ai && root._pendingConfirmAction) {
                        root.ai.sendMessage(root._pendingConfirmAction)
                    }
                }
            }

            AssistantConfirmationDialog {
                id: confirmationDialog
                visible: false

                onConfirmed: {
                    if (root.ai && typeof root.ai.sendMessage !== "undefined") {
                        root.ai.sendMessage("sí")
                    }
                    confirmationDialog.visible = false
                }

                onCancelled: {
                    if (root.ai && typeof root.ai.sendMessage !== "undefined") {
                        root.ai.sendMessage("no")
                    }
                    confirmationDialog.visible = false
                }
            }

            Row {
                id: chatInputRow
                width: parent.width
                spacing: MichiTheme.spacing.sm
                activeFocusOnTab: true
                visible: root.ai !== null

                Rectangle {
                    width: parent.width - MichiTheme.minimumInteractiveSize
                    height: MichiTheme.minimumInteractiveSize
                    radius: MichiTheme.radius.sm
                    color: MichiTheme.colors.surfaceInput
                    border.color: chatInput.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                    border.width: chatInput.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth

                    TextInput {
                        Accessible.role: Accessible.EditableText

                        Accessible.name: qsTr("Campo de texto")

                        id: chatInput
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        anchors.topMargin: MichiTheme.spacing.xs
                        anchors.bottomMargin: MichiTheme.spacing.xs
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        activeFocusOnTab: true
                        enabled: root._aiStatus !== "executing" && root._aiStatus !== "understanding" && root._aiStatus !== "planning"

                        verticalAlignment: TextInput.AlignVCenter

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root._aiStatus === "executing" || root._aiStatus === "understanding"
                                ? "Procesando..."
                                : "Pregunta a Michi AI..."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            visible: parent.text === "" && !parent.activeFocus
                        }

                        onAccepted: sendMessage()
                        Keys.onReturnPressed: sendMessage()
                        Keys.onEscapePressed: {
                            if (root._executing && root.ai && typeof root.ai.cancel !== "undefined") {
                                root.ai.cancel()
                            } else {
                                text = ""
                                focus = false
                            }
                        }
                    }
                }
                    Accessible.role: Accessible.Button


                MichiIconButton {
                    id: sendBtn
                    objectName: "assistantSendButton"
                    iconText: root._executing ? "■" : ">"
                    accessibleName: root._executing ? "Cancelar ejecución" : "Enviar mensaje"
                    tooltipText: root._executing ? "Cancelar" : "Enviar"
                    btnSize: MichiTheme.minimumInteractiveSize
                    activeFocusOnTab: true
                    KeyNavigation.backtab: chatInput
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    onClicked: {
                        if (root._executing) {
                            if (root.ai && typeof root.ai.cancel !== "undefined") {
                                root.ai.cancel()
                            }
                        } else {
                            sendMessage()
                        }
                    }
                }
            }

            StatusBadge {
                id: aiStatusBadge
                text: root.ai === null
                    ? "Asistente no disponible"
                    : root._aiStatus === "executing"
                        ? "Ejecutando acción..."
                        : root._aiStatus === "planning"
                            ? "Planificando..."
                            : root._aiStatus === "cancelling"
                                ? "Cancelando..."
                                : root._aiStatus === "cancelled"
                                    ? "Acción cancelada"
                                    : root._aiStatus === "awaiting_confirmation"
                                        ? "Esperando tu confirmación"
                                        : "Interfaz clásica disponible"
                kind: root.ai === null ? "disconnected"
                    : root._aiStatus === "executing" || root._aiStatus === "planning" ? "active"
                    : root._aiStatus === "cancelled" || root._aiStatus === "failed" ? "warning"
                    : "info"
            }
        }
    }

    function sendMessage() {
        if (!root.ai) return
        var text = chatInput.text.trim()
        if (text === "") return

        root._pendingConfirmAction = text
        chatInput.text = ""
        root.ai.sendMessage(text)
        updateChatHistory()
    }

    function updateChatHistory() {
        if (root.ai && typeof root.ai.getChatHistory !== "undefined") {
            root._chatHistory = parseChatHistory(root.ai.getChatHistory())
        }
    }

    Connections {
        target: root.ai
        function onContextChanged() {
            if (!root.ai) return
            var items = root.ai.suggestions || []
            suggestionsRepeater.model.clear()
            for (var i = 0; i < items.length; i++) {
                suggestionsRepeater.model.append(items[i])
            }
            root._aiStatus = root._normalizeStatus(root.ai.status)
            root.updateChatHistory()
        }

        function onResponseReceived(response) {
            root._aiStatus = root._normalizeStatus(root.ai.status)
            root.updateChatHistory()
        }

        function onStatusChanged(newStatus) {
            root._aiStatus = root._normalizeStatus(newStatus)
        }
    }
}
