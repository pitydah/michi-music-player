import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var ai: typeof michiAiBridge !== "undefined" ? michiAiBridge : null
    property var chatItems: []
    property string pageState: "INITIALIZING"
    property string executionState: ""
    property var pendingAction: null
    property bool destructiveAction: false
    property int affectedCount: 0
    property string contextTrack: ""
    property string contextLibrary: ""
    property var executionResult: ({})
    property var actionHistory: []
    property bool _confirmDialogOpen: false

    objectName: "assistant.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Michi AI"
    Accessible.description: "Asistente inteligente para tu ecosistema musical"

    Component.onCompleted: {
        setState("INITIALIZING")
        if (root.ai && typeof root.ai.refresh !== "undefined") {
            root.ai.refresh()
            setState("READY")
        }
        if (!root.ai) {
            setState("UNAVAILABLE")
        }
    }

    function setState(state) {
        pageState = state
    }

    function setExecutionState(state) {
        executionState = state
    }

    function sendMessage() {
        var text = promptInput.text.trim()
        if (text === "") return
        promptInput.text = ""

        conversation.appendMessage("user", text)

        setExecutionState("PROPOSING")
        setState("LOADING")

        if (root.ai && typeof root.ai.sendMessage !== "undefined") {
            root.ai.sendMessage(text)
        }
    }

    function cancelExecution() {
        if (root.ai && typeof root.ai.cancel !== "undefined") {
            root.ai.cancel()
        }
        setExecutionState("REJECTED")
        setState("READY")
        pendingAction = null
    }

    function confirmAction() {
        if (pendingAction) {
            if (root.ai && typeof root.ai.sendMessage !== "undefined") {
                root.ai.sendMessage("sí")
            }
            setExecutionState("EXECUTING")
            pendingAction = null
        }
        _confirmDialogOpen = false
    }

    function rejectAction() {
        if (root.ai && typeof root.ai.sendMessage !== "undefined") {
            root.ai.sendMessage("no")
        }
        setExecutionState("REJECTED")
        setState("READY")
        pendingAction = null
        _confirmDialogOpen = false
    }

    function retryAction() {
        setExecutionState("EXECUTING")
        setState("LOADING")
    }

    function undoAction() {
        conversation.appendMessage("assistant", "Deshaciendo última acción...")
        setExecutionState("EXECUTING")
        setState("READY")
        executionResult = ({})
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        objectName: "assistant.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (executionState === "EXECUTING" || executionState === "PROPOSING") {
                cancelExecution()
            } else if (promptInput.activeFocus && promptInput.text !== "") {
                promptInput.text = ""
            } else if (typeof navigationBridge !== "undefined" && navigationBridge) {
                navigationBridge.navigate("home")
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                Text {
                    text: "Michi AI"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    text: pageState === "UNAVAILABLE" ? "No disponible" :
                          pageState === "ERROR" ? "Error" :
                          pageState === "LOADING" ? "Procesando..." :
                          pageState === "INITIALIZING" ? "Inicializando..." : ""
                    kind: pageState === "UNAVAILABLE" ? "error" :
                          pageState === "ERROR" ? "error" :
                          pageState === "LOADING" ? "warning" :
                          pageState === "INITIALIZING" ? "info" : "success"
                    visible: pageState !== "READY"
                }
            }

            HeroMaterial {
                width: parent.width
                height: 100
                radius: MichiTheme.radiusLg
                showGlow: true
                objectName: "assistant.hero"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.xl
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Asistente inteligente"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                    }

                    Text {
                        text: "Pregunta, explora y descubre. Reproduce música, busca artistas, crea playlists y más."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width * 0.75
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: contextPreviewRow.height + MichiTheme.spacing.md
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.surfaceCard
                visible: contextTrack !== "" || contextLibrary !== ""

                Row {
                    id: contextPreviewRow
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Contexto:"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: contextTrack
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: contextTrack !== ""
                    }

                    Text {
                        text: contextLibrary
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        anchors.verticalCenter: parent.verticalCenter
                        visible: contextLibrary !== ""
                    }
                }
            }

            Item {
                width: parent.width
                height: parent.height - y
                clip: true

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    AssistantConversation {
                        id: conversation
                        width: parent.width
                        height: conversationHeight
                        aiThinking: pageState === "LOADING"
                        model: root.chatItems
                        objectName: "assistant.conversation"
                    }

                    AssistantActionPreview {
                        id: actionPreview
                        width: parent.width
                        action: root.pendingAction
                        destructive: root.destructiveAction
                        affectedCount: root.affectedCount
                        visible: root.pendingAction !== null
                        objectName: "assistant.actionPreview"
                        onConfirmTriggered: root.confirmAction()
                        onRejectTriggered: root.rejectAction()
                    }

                    AssistantExecutionResult {
                        id: executionResultItem
                        width: parent.width
                        resultStatus: root.executionResult.status || ""
                        resultDetails: root.executionResult.details || ({})
                        errorMessage: root.executionResult.error || ""
                        partialCount: root.executionResult.partialCount || 0
                        totalCount: root.executionResult.totalCount || 0
                        visible: root.executionResult.status !== undefined && root.executionResult.status !== ""
                        objectName: "assistant.executionResult"
                        onRetryTriggered: root.retryAction()
                        onUndoTriggered: root.undoAction()
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                objectName: "assistant.inputRow"

                Rectangle {
                    width: parent.width - sendBtn.width - MichiTheme.spacing.sm
                    height: 40
                    radius: MichiTheme.radiusSm
                    color: MichiTheme.colors.surfaceInput
                    border.color: promptInput.activeFocus ? MichiTheme.colors.borderFocus : MichiTheme.colors.borderSubtle
                    border.width: promptInput.activeFocus ? MichiTheme.borderWidthFocus : MichiTheme.borderWidth

                    TextInput {
                        id: promptInput
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        anchors.topMargin: MichiTheme.spacing.xs
                        anchors.bottomMargin: MichiTheme.spacing.xs
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        verticalAlignment: TextInput.AlignVCenter
                        objectName: "assistant.promptInput"
                        activeFocusOnTab: true
                        enabled: pageState !== "UNAVAILABLE"

                        Accessible.role: Accessible.EditableText
                        Accessible.name: "Entrada de texto"
                        Accessible.description: "Escribe tu mensaje para Michi AI"

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Pregunta a Michi AI..."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            visible: parent.text === "" && !parent.activeFocus
                        }

                        Keys.onReturnPressed: root.sendMessage()
                        Keys.onEscapePressed: {
                            if (text !== "") text = ""
                            else focus = false
                        }

                        onAccepted: root.sendMessage()
                    }

                    HoverHandler { cursorShape: Qt.IBeamCursor }
                }

                MichiIconButton {
                    id: sendBtn
                    iconSource: "../../icons/sidebar_add.svg"
                    iconText: executionState === "EXECUTING" ? "■" : ">"
                    tooltipText: executionState === "EXECUTING" ? "Cancelar" : "Enviar"
                    btnSize: 40
                    objectName: executionState === "EXECUTING" ? "assistant.cancelButton" : "assistant.sendButton"
                    Accessible.name: executionState === "EXECUTING" ? "Cancelar ejecución" : "Enviar mensaje"
                    Accessible.description: executionState === "EXECUTING" ? "Cancela la ejecución en curso" : ""
                    onClicked: {
                        if (executionState === "EXECUTING") {
                            cancelExecution()
                        } else {
                            root.sendMessage()
                        }
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                visible: pageState === "READY" && chatItems.length === 0

                Repeater {
                    model: root.ai ? root.ai.suggestions : []

                    GlassMaterial {
                        width: Math.min(suggestionText.width + MichiTheme.spacing.xl * 2, parent.width)
                        height: 36
                        radius: MichiTheme.radiusPill
                        variant: "base"
                        hovered: suggestionMouse.containsMouse

                        Text {
                            id: suggestionText
                            anchors.centerIn: parent
                            text: modelData.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.metaSize
                        }

                        MouseArea {
                            id: suggestionMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                promptInput.text = modelData.title || ""
                                promptInput.forceActiveFocus()
                            }
                        }
                    }
                }
            }
        }
    }

    AssistantConfirmationDialog {
        id: confirmDialog
        anchors.fill: parent
        open: _confirmDialogOpen
        destructive: root.destructiveAction
        affectedCount: root.affectedCount
        actionDetails: root.pendingAction || ({})
        message: root.destructiveAction ? "Esta acción destructiva se aplicará a los elementos seleccionados." : "¿Confirmas esta acción?"
        title: root.destructiveAction ? "Confirmar acción destructiva" : "Confirmar acción"
        objectName: "assistant.confirmationDialog"
        onConfirmed: root.confirmAction()
        onCancelled: root.rejectAction()
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
        }
    }
}
