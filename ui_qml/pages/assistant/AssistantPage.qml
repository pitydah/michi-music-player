import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Michi AI"

    property var ai: typeof michiAiBridge !== "undefined" ? michiAiBridge : null
    property bool _initialized: false
    property string _aiStatus: root.ai ? root.ai.status || "idle" : "unavailable"
    property string _lastError: root.ai ? root.ai.lastError || "" : "No disponible"
    property var _chatHistory: root.ai ? parseChatHistory(root.ai.getChatHistory()) : []

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

    function showResultForStatus() {
        if (root._aiStatus === "completed") {
            executionResult.status = "success"
            executionResult.summaryText = "Acción ejecutada correctamente."
            executionResult.visible = true
        } else if (root._aiStatus === "failed") {
            executionResult.status = "failure"
            executionResult.summaryText = "Error al ejecutar la acción."
            executionResult.detailText = root._lastError
            executionResult.visible = true
        } else if (root._aiStatus === "partially_executed") {
            executionResult.status = "partial"
            executionResult.summaryText = "Acción ejecutada parcialmente."
            executionResult.visible = true
        }
    }

    Component.onCompleted: {
        setState("INITIALIZING")
        if (root.ai && typeof root.ai.refresh !== "undefined") {
            root.ai.refresh()
            setState("READY")
        }
        if (!root.ai) {
            setState("UNAVAILABLE")
        }
        root._initialized = true
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Row {
                id: headerRow
                width: parent.width
                spacing: MichiTheme.spacing.sm
                objectName: "assistant.headerRow"

                Text {
                    id: titleText
                    text: "Michi AI"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: "assistant.title"
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Michi AI"
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    id: stateBadge
                    text: pageState === "UNAVAILABLE" ? "No disponible" :
                          pageState === "ERROR" ? "Error" :
                          pageState === "LOADING" ? "Procesando..." :
                          pageState === "INITIALIZING" ? "Inicializando..." : ""
                    kind: pageState === "UNAVAILABLE" ? "error" :
                          pageState === "ERROR" ? "error" :
                          pageState === "LOADING" ? "warning" :
                          pageState === "INITIALIZING" ? "info" : "success"
                    visible: pageState !== "READY"
                    objectName: "assistant.stateBadge"
                }
            }

            HeroMaterial {
                id: aiHero
                width: parent.width
                height: 100
                radius: MichiTheme.radiusLg
                showGlow: root.ai !== null
                objectName: "aiHero"
                Accessible.name: "Michi AI"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xs

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
                            text: root.ai ? (root._aiStatus === "idle" ? "Listo" : root._aiStatus) : "No disponible"
                            kind: root.ai ? (root._aiStatus === "idle" || root._aiStatus === "completed" ? "success" : root._aiStatus === "failed" || root._aiStatus === "unavailable" ? "error" : root._aiStatus === "executing" ? "active" : "info") : "disconnected"
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        StatusBadge {
                            text: "Experimental"
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
                        width: parent.width * 0.75
                        wrapMode: Text.WordWrap
                    }
                }
            }

            SectionHeader {
                id: suggestionsHeader
                text: "Sugerencias"
                width: parent.width
                objectName: "suggestionsHeader"
                Accessible.name: "Sugerencias"
            }

                Column {
                    width: parent.width
                    suggestionTitle: model.title || ""
                    suggestionDescription: model.description || ""
                    actionRoute: model.route || ""
                    objectName: "suggestionCard_" + index
                    Accessible.name: model.title || "Sugerencia"
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
                objectName: "assistantConversation"
                Accessible.name: "Conversación"
            }

            AssistantActionPreview {
                id: actionPreview
                width: parent.width
                visible: false
                objectName: "assistantActionPreview"
                Accessible.name: "Vista previa de acción"

                onConfirm: {
                    if (root.ai && typeof root.ai.sendMessage !== "undefined") {
                        root.ai.sendMessage("sí")
                    }
                    actionPreview.visible = false
                }

                onReject: {
                    if (root.ai && typeof root.ai.sendMessage !== "undefined") {
                        root.ai.sendMessage("no")
                    }
                    actionPreview.visible = false
                }
            }

            AssistantExecutionResult {
                id: executionResult
                width: parent.width
                visible: false
                objectName: "assistantExecutionResult"
                Accessible.name: "Resultado de ejecución"

                onRetry: {
                    executionResult.visible = false
                    if (root.ai && root._pendingConfirmAction) {
                        root.ai.sendMessage(root._pendingConfirmAction)
                    }
                }
            }

            AssistantConfirmationDialog {
                id: confirmationDialog
                objectName: "assistantConfirmationDialog"
                Accessible.name: "Diálogo de confirmación"
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
                    radius: MichiTheme.radiusSm
                    color: MichiTheme.colors.surfaceInput
                    border.color: chatInput.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                    border.width: chatInput.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth
                    objectName: "chatInputBackground"
                    Accessible.name: "Entrada de chat"

                    TextInput {
                        id: promptInput
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        anchors.topMargin: MichiTheme.spacing.xs
                        anchors.bottomMargin: MichiTheme.spacing.xs
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        objectName: "chatInput"
                        Accessible.name: "Pregunta a Michi AI"
                        activeFocusOnTab: true
                        enabled: root._aiStatus !== "executing" && root._aiStatus !== "understanding" && root._aiStatus !== "planning"

                        verticalAlignment: TextInput.AlignVCenter
                        objectName: "assistant.promptInput"
                        activeFocusOnTab: true
                        enabled: pageState !== "UNAVAILABLE"

                        Accessible.role: Accessible.EditableText
                        Accessible.name: "Entrada de texto"
                        Accessible.description: "Escribe tu mensaje para Michi AI"

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

                    HoverHandler { cursorShape: Qt.IBeamCursor }
                }

                MichiIconButton {
                    id: sendBtn
                    iconText: root._executing ? "■" : ">"
                    tooltipText: root._executing ? "Cancelar" : "Enviar"
                    btnSize: MichiTheme.minimumInteractiveSize
                    objectName: "sendMessageButton"
                    Accessible.name: root._executing ? "Cancelar" : "Enviar mensaje"
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
                    : root._executing
                        ? "Ejecutando acción..."
                        : root._aiStatus === "cancelled"
                            ? "Acción cancelada"
                            : "Interfaz clásica disponible"
                kind: root.ai === null ? "disconnected" : root._executing ? "active" : "info"
                objectName: "aiStatusBadge"
                Accessible.name: "Estado de Michi AI"
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
            setState("READY")
        }
    }

    Connections {
        target: root.ai
        function onResponseReceived(response) {
            if (root.ai) {
                conversation.appendMessage("assistant", response)
                setState("READY")

                if (root.ai.status === "awaiting_confirmation") {
                    setExecutionState("PROPOSING")
                    pendingAction = { description: "acción pendiente" }
                    destructiveAction = false
                    _confirmDialogOpen = true
                } else if (root.ai.status === "executing") {
                    setExecutionState("EXECUTING")
                } else if (root.ai.status === "completed") {
                    setExecutionState("EXECUTED")
                    executionResult = { status: "success" }
                } else if (root.ai.status === "failed") {
                    setExecutionState("FAILED")
                    executionResult = { status: "failed", error: root.ai.lastError || "Error desconocido" }
                } else if (root.ai.status === "cancelled") {
                    setExecutionState("REJECTED")
                } else {
                    setExecutionState("")
                    setState("READY")
                }
            }
            root._aiStatus = root.ai.status || "idle"
            root.updateChatHistory()
        }

        function onResponseReceived(response) {
            root._aiStatus = root.ai.status || "idle"
            root.updateChatHistory()
        }

        function onStatusChanged(newStatus) {
            root._aiStatus = newStatus
        }
    }
}
