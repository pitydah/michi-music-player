import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "distributionHubPage"
    focus: true

    property var bridge: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property string selectedSourceId: ""
    property var selectedDestinationIds: []
    property string feedback: ""
    property bool feedbackError: false
    property string editingRouteId: ""
    readonly property bool operationBusy: root.bridge ? root.bridge.operationInProgress : false

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Distribución de audio")

    function statusKind(state) {
        if (state === "active" || state === "running" || state === "online" || state === "ready")
            return "success"
        if (state === "error" || state === "offline" || state === "unavailable")
            return "error"
        if (state === "degraded" || state === "starting" || state === "stopping")
            return "warning"
        return "info"
    }

    function showResult(result, successText) {
        root.feedbackError = !result || !result.ok
        if (root.feedbackError)
            root.feedback = qsTr("No se pudo completar la operación: %1").arg(result && result.error ? result.error : qsTr("error desconocido"))
        else if (result.pending)
            root.feedback = qsTr("Operación en curso…")
        else
            root.feedback = successText
        if (root.bridge && !result.pending)
            root.bridge.refreshDistribution()
    }

    function toggleDestination(destinationId, checked) {
        var next = root.selectedDestinationIds.slice(0)
        var index = next.indexOf(destinationId)
        if (checked && index < 0)
            next.push(destinationId)
        else if (!checked && index >= 0)
            next.splice(index, 1)
        root.selectedDestinationIds = next
    }

    Component.onCompleted: {
        if (root.bridge)
            root.bridge.refreshDistribution()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            spacing: MichiTheme.spacing.md

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Label {
                    text: qsTr("Distribución de audio")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Label {
                    Layout.fillWidth: true
                    text: qsTr("Gestiona fuentes, Snapserver, receptores, destinos y rutas verificadas de audio.")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                }
            }

            StatusBadge {
                text: root.bridge ? root.bridge.distributionState : qsTr("No disponible")
                kind: root.statusKind(root.bridge ? root.bridge.distributionState : "unavailable")
            }

            BusyIndicator {
                running: root.operationBusy
                visible: running
                Layout.preferredWidth: 28
                Layout.preferredHeight: 28
            }

            MichiButton {
                text: qsTr("Actualizar")
                variant: "ghost"
                enabled: !root.operationBusy
                onClicked: {
                    if (root.bridge)
                        root.showResult(root.bridge.refreshDistribution(), qsTr("Estado actualizado."))
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: feedbackLabel.implicitHeight + MichiTheme.spacing.md * 2
            visible: root.feedback !== ""
            radius: MichiTheme.radius.md
            color: MichiTheme.colors.surfaceCard
            border.width: 1
            border.color: root.feedbackError ? MichiTheme.colors.error : MichiTheme.colors.success

            Label {
                id: feedbackLabel
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.md
                text: root.feedback
                color: MichiTheme.colors.textPrimary
                wrapMode: Text.WordWrap
            }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true

            TabButton { text: qsTr("Fuentes") }
            TabButton { text: qsTr("Servidores") }
            TabButton { text: qsTr("Receptores") }
            TabButton { text: qsTr("Destinos") }
            TabButton { text: qsTr("Rutas") }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Fuentes disponibles")
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: !root.bridge || root.bridge.sources.length === 0
                        text: qsTr("No hay streams de audio disponibles. Inicia Snapserver y conecta una fuente real antes de crear rutas.")
                        color: MichiTheme.colors.textMuted
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.bridge ? root.bridge.sources : []

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: sourceRow.implicitHeight + MichiTheme.spacing.md * 2
                            radius: MichiTheme.radius.md
                            color: root.selectedSourceId === modelData.id
                                   ? MichiTheme.colors.accentSurface
                                   : MichiTheme.colors.surfaceCard
                            border.width: 1
                            border.color: root.selectedSourceId === modelData.id
                                          ? MichiTheme.colors.accent
                                          : MichiTheme.colors.borderCard

                            RowLayout {
                                id: sourceRow
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.md

                                RadioButton {
                                    checked: root.selectedSourceId === modelData.id
                                    enabled: modelData.routeable === true
                                    onClicked: root.selectedSourceId = modelData.id
                                    Accessible.name: qsTr("Seleccionar fuente %1").arg(modelData.name || modelData.id)
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text: modelData.name || modelData.id
                                        color: MichiTheme.colors.textPrimary
                                        font.weight: Font.DemiBold
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.routeable
                                              ? qsTr("%1 · %2 Hz · %3 canal(es)").arg(modelData.format || "unknown").arg(modelData.sample_rate || 0).arg(modelData.channels || 0)
                                              : (modelData.reason || qsTr("Fuente informativa; todavía no enrutable"))
                                        color: MichiTheme.colors.textSecondary
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                StatusBadge {
                                    text: modelData.routeable ? (modelData.state || qsTr("disponible")) : qsTr("No enrutable")
                                    kind: modelData.routeable ? root.statusKind(modelData.state) : "warning"
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Servidores de distribución")
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: !root.bridge || root.bridge.servers.length === 0
                        text: qsTr("No existe un administrador de Snapserver disponible en esta instalación.")
                        color: MichiTheme.colors.textMuted
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.bridge ? root.bridge.servers : []

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: serverRow.implicitHeight + MichiTheme.spacing.md * 2
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.surfaceCard
                            border.width: 1
                            border.color: MichiTheme.colors.borderCard

                            RowLayout {
                                id: serverRow
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.md

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text: modelData.name || qsTr("Snapserver")
                                        color: MichiTheme.colors.textPrimary
                                        font.weight: Font.DemiBold
                                    }

                                    Label {
                                        text: qsTr("Audio %1 · Control %2 · Web %3")
                                              .arg(modelData.tcp_port || 1704)
                                              .arg(modelData.control_port || 1705)
                                              .arg(modelData.http_port || 1780)
                                        color: MichiTheme.colors.textSecondary
                                    }

                                    Label {
                                        Layout.fillWidth: true
                                        visible: modelData.error
                                        text: modelData.error || ""
                                        color: MichiTheme.colors.error
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                StatusBadge {
                                    text: modelData.state || qsTr("desconocido")
                                    kind: root.statusKind(modelData.state)
                                }

                                MichiButton {
                                    text: modelData.state === "running" ? qsTr("Detener") : qsTr("Iniciar")
                                    variant: modelData.state === "running" ? "danger" : "primary"
                                    visible: modelData.id === "local_snapserver"
                                    enabled: modelData.binary_available !== false && !root.operationBusy
                                    onClicked: {
                                        var result = modelData.state === "running"
                                                   ? root.bridge.stopServer(modelData.id)
                                                   : root.bridge.startServer(modelData.id)
                                        root.showResult(result, modelData.state === "running" ? qsTr("Detención solicitada.") : qsTr("Inicio solicitado."))
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    RowLayout {
                        Layout.fillWidth: true

                        SectionHeader {
                            Layout.fillWidth: true
                            text: qsTr("Receptores detectados")
                        }

                        MichiButton {
                            text: qsTr("Detectar")
                            variant: "ghost"
                            enabled: !root.operationBusy
                            onClicked: root.showResult(root.bridge.discoverReceivers(), qsTr("Descubrimiento completado."))
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: !root.bridge || root.bridge.receiverList.length === 0
                        text: qsTr("No se detectaron Snapclients ni receptores Michi Music Stream.")
                        color: MichiTheme.colors.textMuted
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.bridge ? root.bridge.receiverList : []

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: receiverColumn.implicitHeight + MichiTheme.spacing.md * 2
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.surfaceCard
                            border.width: 1
                            border.color: MichiTheme.colors.borderCard

                            ColumnLayout {
                                id: receiverColumn
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                RowLayout {
                                    Layout.fillWidth: true

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Label {
                                            text: modelData.name || modelData.id
                                            color: MichiTheme.colors.textPrimary
                                            font.weight: Font.DemiBold
                                        }

                                        Label {
                                            text: qsTr("%1 · Grupo: %2").arg(modelData.host || modelData.backend || "snapcast").arg(modelData.group_name || modelData.group || qsTr("sin grupo"))
                                            color: MichiTheme.colors.textSecondary
                                        }
                                    }

                                    StatusBadge {
                                        text: modelData.state || (modelData.connected ? qsTr("online") : qsTr("offline"))
                                        kind: root.statusKind(modelData.state || (modelData.connected ? "online" : "offline"))
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    enabled: modelData.connected === true
                                    spacing: MichiTheme.spacing.md

                                    Label {
                                        text: qsTr("Volumen")
                                        color: MichiTheme.colors.textSecondary
                                    }

                                    MichiSlider {
                                        id: receiverVolume
                                        Layout.fillWidth: true
                                        from: 0
                                        to: 100
                                        value: modelData.volume !== undefined ? modelData.volume : 100
                                        onPressedChanged: {
                                            if (!pressed && !root.operationBusy)
                                                root.showResult(root.bridge.setReceiverVolume(modelData.id, Math.round(value)), qsTr("Volumen actualizado."))
                                        }
                                    }

                                    CheckBox {
                                        text: qsTr("Mute")
                                        checked: modelData.muted === true
                                        enabled: !root.operationBusy
                                        onClicked: root.showResult(root.bridge.setReceiverMute(modelData.id, checked), qsTr("Mute actualizado."))
                                    }

                                    Label {
                                        text: qsTr("Latencia")
                                        color: MichiTheme.colors.textSecondary
                                    }

                                    SpinBox {
                                        from: 0
                                        to: 5000
                                        value: modelData.latency_ms || 0
                                        editable: true
                                        enabled: !root.operationBusy
                                        onValueModified: root.showResult(root.bridge.setReceiverLatency(modelData.id, value), qsTr("Latencia actualizada."))
                                        Accessible.name: qsTr("Latencia de %1").arg(modelData.name || modelData.id)
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    enabled: modelData.connected === true && !root.operationBusy
                                    spacing: MichiTheme.spacing.sm

                                    TextField {
                                        id: receiverName
                                        Layout.fillWidth: true
                                        text: modelData.name || ""
                                        placeholderText: qsTr("Nombre del receptor")
                                        Accessible.name: qsTr("Nombre de %1").arg(modelData.name || modelData.id)
                                    }

                                    MichiButton {
                                        text: qsTr("Renombrar")
                                        variant: "ghost"
                                        enabled: receiverName.text.trim() !== "" && receiverName.text.trim() !== (modelData.name || "")
                                        onClicked: root.showResult(root.bridge.setReceiverName(modelData.id, receiverName.text), qsTr("Receptor renombrado."))
                                    }

                                    ComboBox {
                                        id: receiverGroup
                                        model: root.bridge ? root.bridge.destinations : []
                                        textRole: "name"
                                        valueRole: "id"
                                        currentIndex: indexOfValue(modelData.group)
                                        Accessible.name: qsTr("Mover %1 a otro grupo").arg(modelData.name || modelData.id)
                                        onActivated: {
                                            if (currentValue && currentValue !== modelData.group)
                                                root.showResult(root.bridge.moveReceiver(modelData.id, currentValue), qsTr("Receptor movido y verificado."))
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Destinos de ruta")
                    }

                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Selecciona una o más zonas Snapcast. Los dispositivos de Home Assistant permanecen visibles en Habitaciones, pero no se marcan como enrutables sin un transporte de audio verificable.")
                        color: MichiTheme.colors.textSecondary
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: !root.bridge || root.bridge.destinations.length === 0
                        text: qsTr("No hay destinos enrutables disponibles.")
                        color: MichiTheme.colors.textMuted
                    }

                    Repeater {
                        model: root.bridge ? root.bridge.destinations : []

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: destinationRow.implicitHeight + MichiTheme.spacing.md * 2
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.surfaceCard
                            border.width: 1
                            border.color: MichiTheme.colors.borderCard

                            RowLayout {
                                id: destinationRow
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.md

                                CheckBox {
                                    enabled: modelData.routeable === true
                                    checked: root.selectedDestinationIds.indexOf(modelData.id) >= 0
                                    onClicked: root.toggleDestination(modelData.id, checked)
                                    Accessible.name: qsTr("Seleccionar destino %1").arg(modelData.name || modelData.id)
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Label {
                                        text: modelData.name || modelData.id
                                        color: MichiTheme.colors.textPrimary
                                        font.weight: Font.DemiBold
                                    }

                                    Label {
                                        text: qsTr("%1 miembro(s) · Stream actual: %2")
                                              .arg(modelData.members ? modelData.members.length : 0)
                                              .arg(modelData.stream_id || qsTr("ninguno"))
                                        color: MichiTheme.colors.textSecondary
                                    }
                                }

                                StatusBadge {
                                    text: modelData.routeable ? (modelData.state || qsTr("configurado")) : qsTr("No enrutable")
                                    kind: modelData.routeable ? root.statusKind(modelData.state) : "warning"
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            ScrollView {
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Crear ruta")
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: routeBuilder.implicitHeight + MichiTheme.spacing.md * 2
                        radius: MichiTheme.radius.md
                        color: MichiTheme.colors.surfaceCard
                        border.width: 1
                        border.color: MichiTheme.colors.borderCard

                        ColumnLayout {
                            id: routeBuilder
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.md
                            spacing: MichiTheme.spacing.sm

                            TextField {
                                id: routeName
                                Layout.fillWidth: true
                                placeholderText: qsTr("Nombre de la ruta")
                                Accessible.name: qsTr("Nombre de la ruta")
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.selectedSourceId
                                      ? qsTr("Fuente: %1").arg(root.selectedSourceId)
                                      : qsTr("Selecciona una fuente enrutable en la pestaña Fuentes.")
                                color: root.selectedSourceId ? MichiTheme.colors.textPrimary : MichiTheme.colors.warning
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.selectedDestinationIds.length > 0
                                      ? qsTr("%1 destino(s) seleccionado(s)").arg(root.selectedDestinationIds.length)
                                      : qsTr("Selecciona destinos en la pestaña Destinos.")
                                color: root.selectedDestinationIds.length > 0 ? MichiTheme.colors.textPrimary : MichiTheme.colors.warning
                            }

                            MichiButton {
                                text: root.editingRouteId ? qsTr("Guardar cambios") : qsTr("Crear ruta")
                                variant: "primary"
                                enabled: !root.operationBusy && root.selectedSourceId !== "" && root.selectedDestinationIds.length > 0
                                onClicked: {
                                    var result = root.editingRouteId
                                               ? root.bridge.updateRoute(root.editingRouteId, routeName.text, root.selectedSourceId, root.selectedDestinationIds)
                                               : root.bridge.createRoute(routeName.text, root.selectedSourceId, root.selectedDestinationIds)
                                    root.showResult(result, root.editingRouteId ? qsTr("Ruta actualizada.") : qsTr("Ruta creada y pendiente de activación."))
                                    if (result && result.ok) {
                                        routeName.clear()
                                        root.editingRouteId = ""
                                    }
                                }
                            }

                            MichiButton {
                                text: qsTr("Cancelar edición")
                                variant: "ghost"
                                visible: root.editingRouteId !== ""
                                enabled: !root.operationBusy
                                onClicked: {
                                    root.editingRouteId = ""
                                    routeName.clear()
                                }
                            }
                        }
                    }

                    SectionHeader {
                        Layout.fillWidth: true
                        text: qsTr("Rutas configuradas")
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: !root.bridge || root.bridge.routes.length === 0
                        text: qsTr("Todavía no existen rutas configuradas.")
                        color: MichiTheme.colors.textMuted
                    }

                    Repeater {
                        model: root.bridge ? root.bridge.routes : []

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: routeColumn.implicitHeight + MichiTheme.spacing.md * 2
                            radius: MichiTheme.radius.md
                            color: MichiTheme.colors.surfaceCard
                            border.width: 1
                            border.color: modelData.state === "error" ? MichiTheme.colors.error : MichiTheme.colors.borderCard

                            ColumnLayout {
                                id: routeColumn
                                anchors.fill: parent
                                anchors.margins: MichiTheme.spacing.md
                                spacing: MichiTheme.spacing.sm

                                RowLayout {
                                    Layout.fillWidth: true

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        Label {
                                            text: modelData.name || modelData.id
                                            color: MichiTheme.colors.textPrimary
                                            font.weight: Font.DemiBold
                                        }

                                        Label {
                                            Layout.fillWidth: true
                                            text: qsTr("%1 → %2 destino(s)").arg(modelData.source_id || "").arg(modelData.destination_ids ? modelData.destination_ids.length : 0)
                                            color: MichiTheme.colors.textSecondary
                                            wrapMode: Text.WordWrap
                                        }
                                    }

                                    StatusBadge {
                                        text: modelData.state || qsTr("configurada")
                                        kind: root.statusKind(modelData.state)
                                    }
                                }

                                Label {
                                    Layout.fillWidth: true
                                    visible: modelData.error
                                    text: modelData.error || ""
                                    color: MichiTheme.colors.error
                                    wrapMode: Text.WordWrap
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: MichiTheme.spacing.sm

                                    MichiButton {
                                        text: modelData.state === "active" || modelData.state === "degraded" ? qsTr("Detener") : qsTr("Activar")
                                        variant: modelData.state === "active" ? "danger" : "primary"
                                        enabled: !root.operationBusy
                                        onClicked: {
                                            var result = modelData.state === "active" || modelData.state === "degraded"
                                                       ? root.bridge.stopRoute(modelData.id)
                                                       : root.bridge.startRoute(modelData.id)
                                            root.showResult(result, modelData.state === "active" ? qsTr("Ruta detenida y stream anterior restaurado.") : qsTr("Ruta activada y verificada."))
                                        }
                                    }

                                    MichiButton {
                                        text: qsTr("Recuperar")
                                        variant: "ghost"
                                        visible: modelData.state === "error" || modelData.state === "degraded"
                                        enabled: !root.operationBusy
                                        onClicked: root.showResult(root.bridge.retryRoute(modelData.id), qsTr("Recuperación completada."))
                                    }

                                    MichiButton {
                                        text: qsTr("Editar")
                                        variant: "ghost"
                                        enabled: !root.operationBusy && modelData.state !== "active" && modelData.state !== "degraded"
                                        onClicked: {
                                            root.editingRouteId = modelData.id
                                            routeName.text = modelData.name || ""
                                            root.selectedSourceId = modelData.source_id || ""
                                            root.selectedDestinationIds = modelData.destination_ids ? modelData.destination_ids.slice(0) : []
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    MichiButton {
                                        text: qsTr("Eliminar")
                                        variant: "danger"
                                        enabled: modelData.state !== "active" && modelData.state !== "degraded"
                                        onClicked: root.showResult(root.bridge.deleteRoute(modelData.id), qsTr("Ruta eliminada."))
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    Connections {
        target: root.bridge
        function onOperationFinished(result) {
            root.feedbackError = !result || !result.ok
            root.feedback = root.feedbackError
                          ? qsTr("La operación falló: %1").arg(result && result.error ? result.error : qsTr("error desconocido"))
                          : qsTr("Operación completada y verificada.")
        }
    }
}
