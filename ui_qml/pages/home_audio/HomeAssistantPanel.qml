import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Home Assistant")
    objectName: "homeAssistantPanel"
    focus: true
    id: root

    property string state: "not_configured"
    property bool loading: false
    property bool hasError: false
    property string lastError: ""
    property string host: ""
    property int port: 8123
    property string token: ""
    property var selectedEntityIds: []
    property bool selectionDirty: false
    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null

    readonly property var discoveredInstances: root.bridge
                                               ? root.bridge.homeAssistantInstances || []
                                               : []
    readonly property var entities: root.bridge ? root.bridge.devices || [] : []

    signal configureClicked(string host, int port, string token)
    signal disconnectClicked()
    signal openDiagnostics()

    readonly property real cardHeight: root.state === "not_configured"
                                       ? (responsive.compact ? 720 : 600)
                                       : (responsive.compact ? 760 : 620)

    implicitHeight: root.loading ? 160 : root.cardHeight

    MichiResponsive {
        id: responsive
        availableWidth: root.width
    }

    function routeEnter(route, params) {
        if (!root.bridge) return
        var s = root.bridge.homeAssistantState
        if (s !== undefined)
            root.state = s
        root.syncSelectedEntities()
    }

    function syncSelectedEntities() {
        if (root.selectionDirty)
            return
        var selected = []
        for (var index = 0; index < root.entities.length; index++) {
            var entity = root.entities[index]
            if (entity.imported !== false)
                selected.push(entity.entity_id)
        }
        root.selectedEntityIds = selected
    }

    function isEntitySelected(entityId) {
        return root.selectedEntityIds.indexOf(entityId) >= 0
    }

    function setEntitySelected(entityId, selected) {
        var next = root.selectedEntityIds.slice()
        var index = next.indexOf(entityId)
        if (selected && index < 0)
            next.push(entityId)
        else if (!selected && index >= 0)
            next.splice(index, 1)
        root.selectedEntityIds = next
        root.selectionDirty = true
    }

    function useDiscoveredInstance(instance) {
        root.host = instance.host || instance.hostname || ""
        root.port = instance.port || 8123
    }

    // Loading state
    Loader {
        anchors.fill: parent
        active: root.loading
        sourceComponent: MichiLoadingState { title: qsTr("Conectando con Home Assistant...") }
    }

    // Error state
    Loader {
        anchors.fill: parent
        active: root.hasError && !root.loading
        sourceComponent: Component {
            Column {
                spacing: MichiTheme.spacing.md
                anchors.centerIn: parent
                width: parent.width - MichiTheme.spacing.xl * 2

                StatusBadge { text: qsTr("Error de conexión"); kind: "error"; anchors.horizontalCenter: parent.horizontalCenter }

                Text {
                    width: parent.width
                    text: root.lastError || qsTr("No se pudo conectar con Home Assistant. Verifique el host, puerto y token.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }

                MichiButton {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: qsTr("Reintentar")
                    variant: "primary"
                    onClicked: {
                        root.hasError = false
                        root.state = "not_configured"
                    }
                }
            }
        }
    }

    // Configured/connected state
    Column {
        anchors.fill: parent
        spacing: MichiTheme.spacing.lg
        visible: !root.loading && !root.hasError

        GlassMaterial {
            width: parent.width
            height: root.cardHeight
            variant: "base"
            radius: MichiTheme.radius.md

            Column {
                anchors.fill: parent
                anchors.margins: responsive.compact
                                 ? MichiTheme.spacing.md
                                 : MichiTheme.spacing.lg
                spacing: MichiTheme.spacing.md

                Text {
                    text: qsTr("Home Assistant")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                TextField {
                    width: parent.width
                    visible: root.state === "not_configured"
                    placeholderText: qsTr("Host de Home Assistant")
                    text: root.host
                    onTextChanged: root.host = text
                    Accessible.name: qsTr("Host de Home Assistant")
                }

                MichiButton {
                    width: parent.width
                    visible: root.state === "not_configured"
                    text: qsTr("Detectar Home Assistant en la red")
                    variant: "ghost"
                    enabled: root.bridge && !root.bridge.operationInProgress
                    onClicked: root.bridge.discoverHomeAssistantInstances()
                }

                ComboBox {
                    width: parent.width
                    visible: root.state === "not_configured"
                             && root.discoveredInstances.length > 0
                    model: root.discoveredInstances
                    textRole: "name"
                    Accessible.name: qsTr("Instancias de Home Assistant detectadas")
                    onActivated: root.useDiscoveredInstance(root.discoveredInstances[currentIndex])
                    onCountChanged: {
                        if (count > 0 && root.host.trim() === "")
                            root.useDiscoveredInstance(root.discoveredInstances[0])
                    }
                }

                SpinBox {
                    width: responsive.compact ? parent.width : Math.min(parent.width, 240)
                    visible: root.state === "not_configured"
                    from: 1; to: 65535
                    value: root.port
                    editable: true
                    onValueModified: root.port = value
                    Accessible.name: qsTr("Puerto de Home Assistant")
                }

                TextField {
                    width: parent.width
                    visible: root.state === "not_configured"
                    placeholderText: qsTr("Token de acceso de larga duración")
                    echoMode: TextInput.Password
                    text: root.token
                    onTextChanged: root.token = text
                    Accessible.name: qsTr("Token de Home Assistant")
                }

                Text {
                    text: root.state === "not_configured"
                        ? qsTr("Home Assistant no está configurado. Conéctalo para controlar la reproducción en tu hogar.")
                        : qsTr("Home Assistant conectado y operativo.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width
                    wrapMode: Text.WordWrap
                }

                Row {
                    width: parent.width
                    spacing: MichiTheme.spacing.sm
                    visible: root.state !== "not_configured"

                    Text {
                        text: qsTr("Entidades media_player")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    StatusBadge {
                        text: root.bridge && root.bridge.haWebSocketConnected
                              ? qsTr("Tiempo real")
                              : qsTr("Actualización periódica")
                        kind: root.bridge && root.bridge.haWebSocketConnected
                              ? "success"
                              : "warning"
                    }
                }

                ListView {
                    id: entityList
                    width: parent.width
                    height: Math.min(contentHeight, responsive.compact ? 300 : 220)
                    visible: root.state !== "not_configured"
                    model: root.entities
                    spacing: MichiTheme.spacing.xs
                    reuseItems: true

                    delegate: Rectangle {
                        required property var modelData

                        width: entityList.width
                        height: MichiTheme.minimumInteractiveSize + MichiTheme.spacing.sm
                        radius: MichiTheme.radius.sm
                        color: MichiTheme.colors.surfaceSubtle
                        border.width: 1
                        border.color: MichiTheme.colors.borderSubtle

                        Row {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.sm

                            CheckBox {
                                anchors.verticalCenter: parent.verticalCenter
                                checked: root.isEntitySelected(modelData.entity_id)
                                Accessible.name: qsTr("Importar %1").arg(modelData.name)
                                onToggled: root.setEntitySelected(modelData.entity_id, checked)
                            }

                            Column {
                                width: Math.max(0, parent.width - stateBadge.width
                                                - MichiTheme.minimumInteractiveSize
                                                - parent.spacing * 2)
                                anchors.verticalCenter: parent.verticalCenter

                                Text {
                                    width: parent.width
                                    text: modelData.name || modelData.entity_id
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    elide: Text.ElideRight
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.entity_id
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.captionSize
                                    elide: Text.ElideRight
                                }
                            }

                            StatusBadge {
                                id: stateBadge
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.state || qsTr("desconocido")
                                kind: modelData.state === "playing" ? "success" : "neutral"
                            }
                        }
                    }
                }

                MichiButton {
                    width: parent.width
                    visible: root.state !== "not_configured" && root.entities.length > 0
                    text: qsTr("Importar entidades seleccionadas (%1)")
                          .arg(root.selectedEntityIds.length)
                    variant: "primary"
                    onClicked: {
                        var result = root.bridge.importHomeAssistantEntities(
                                         root.selectedEntityIds)
                        if (result && result.ok && !result.pending) {
                            root.selectionDirty = false
                            root.selectedEntityIds = result.imported || []
                        }
                    }
                }

                Grid {
                    id: actionGrid
                    width: parent.width
                    columns: Math.min(root.state === "not_configured" ? 2 : 3,
                                      responsive.columnCount)
                    columnSpacing: MichiTheme.spacing.sm
                    rowSpacing: MichiTheme.spacing.sm

                    MichiButton {
                        Accessible.role: Accessible.Button
                        activeFocusOnTab: true
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        text: root.state === "not_configured"
                              ? qsTr("Configurar Home Assistant")
                              : qsTr("Abrir Home Assistant")
                        variant: "primary"
                        enabled: root.state !== "not_configured" || (root.host.trim() !== "" && root.token.trim() !== "")
                        onClicked: {
                            if (root.state === "not_configured") {
                                root.loading = true
                                root.configureClicked(root.host, root.port, root.token)
                            }
                        }
                    }
                    MichiButton {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        text: qsTr("Desconectar")
                        variant: "danger"
                        visible: root.state !== "not_configured"
                        onClicked: root.disconnectClicked()
                    }
                    MichiButton {
                        width: (parent.width - parent.columnSpacing * (parent.columns - 1)) / parent.columns
                        text: qsTr("Diagnóstico")
                        variant: "ghost"
                        onClicked: root.openDiagnostics()
                    }
                }

                StatusBadge {
                    text: root.state === "not_configured" ? qsTr("No configurado") : qsTr("Conectado")
                    kind: root.state === "not_configured" ? "disconnected" : "success"
                }
            }
        }
    }

    Connections {
        target: root.bridge
        function onStateChanged() {
            if (!root.bridge) return
            var s = root.bridge.homeAssistantState
            if (s !== undefined) {
                root.state = s
                if (s === "error") {
                    root.hasError = true
                    root.lastError = root.bridge.lastError || qsTr("Error de conexión")
                }
                root.loading = false
                root.syncSelectedEntities()
            }
        }
        function onOperationFinished(result) {
            if (result && result.imported !== undefined) {
                root.selectionDirty = false
                root.selectedEntityIds = result.imported
            }
        }
    }
}
