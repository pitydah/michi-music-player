import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"

Item {
    id: root
    objectName: "home_audio.zone_detail.page"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: zoneName !== "" ? qsTr("Zona %1").arg(zoneName)
                                     : qsTr("Detalle de zona")
    Accessible.description: qsTr("Controles de volumen, fuente, latencia y dispositivos")

    property var ha: typeof homeAudioBridge !== "undefined" ? homeAudioBridge : null
    property string zoneId: ""
    property string zoneName: ""
    property int zoneVolume: 50
    property bool zoneMuted: false
    property string zoneSource: ""
    property string zoneStatus: "idle"
    property int zoneLatencyMs: 0
    property var zoneDevices: []
    property bool zoneOnline: true
    property string zoneState: root.ha ? "ready" : "unavailable"
    property string errorMessage: ""

diff a/ui_qml/pages/home_audio/ZoneDetailPage.qml b/ui_qml/pages/home_audio/ZoneDetailPage.qml	(rejected hunks)
@@ -31,4 +50,517 @@ Item {
     signal groupClicked(string zoneId)
     signal ungroupClicked(string zoneId)
     signal renameRequested(string zoneId, string newName)
-    signal deleteR
\ No newline at end of file
+    signal deleteRequested(string zoneId)
+
+    MichiResponsive {
+        id: responsive
+        availableWidth: root.width
+    }
+
+    function _zoneForId(id) {
+        var zones = root.ha && root.ha.zones ? root.ha.zones : []
+        for (var i = 0; i < zones.length; ++i) {
+            if (String(zones[i].id || "") === String(id || ""))
+                return zones[i]
+        }
+        return null
+    }
+
+    function _applyZone(zone) {
+        if (!zone)
+            return
+        root.zoneName = zone.name || qsTr("Zona de audio")
+        var rawVolume = Number(zone.volume !== undefined ? zone.volume : 50)
+        root.zoneVolume = Math.round(rawVolume <= 1 ? rawVolume * 100 : rawVolume)
+        root.zoneMuted = Boolean(zone.muted)
+        root.zoneSource = zone.source || ""
+        root.zoneStatus = zone.state || zone.status || "idle"
+        root.zoneLatencyMs = Number(zone.latency_ms || 0)
+        root.zoneDevices = zone.devices || zone.members || []
+        root.zoneOnline = zone.online !== false && root.zoneStatus !== "offline"
+    }
+
+    function refreshHeaderContext() {
+        if (!root.ha) {
+            root.zoneState = "unavailable"
+            return
+        }
+        root.zoneState = "loading"
+        var result = typeof root.ha.refresh === "function" ? root.ha.refresh() : { ok: true }
+        if (result && result.ok === false) {
+            root.errorMessage = result.error || qsTr("No se pudo actualizar la zona.")
+            root.zoneState = "error"
+            return
+        }
+        var zone = root._zoneForId(root.zoneId)
+        if (!zone) {
+            root.errorMessage = qsTr("La zona solicitada ya no existe o no está conectada.")
+            root.zoneState = "empty"
+            return
+        }
+        root._applyZone(zone)
+        root.errorMessage = ""
+        root.zoneState = "ready"
+    }
+
+    function routeEnter(route, params) {
+        if (params) {
+            root.zoneId = params.zoneId || params.zone_id || root.zoneId
+            if (params.zoneName)
+                root.zoneName = params.zoneName
+        }
+        root.refreshHeaderContext()
+    }
+
+    function _showOperationError(result, fallback) {
+        if (result && result.ok !== false)
+            return false
+        root.errorMessage = result && result.error ? result.error : fallback
+        root.zoneState = "error"
+        return true
+    }
+
+    AsyncStateView {
+        anchors.fill: parent
+        state: root.zoneState === "loading" ? AsyncStateView.LOADING
+             : root.zoneState === "error" ? AsyncStateView.ERROR
+             : root.zoneState === "empty" ? AsyncStateView.EMPTY
+             : root.zoneState === "unavailable" ? AsyncStateView.UNAVAILABLE
+             : AsyncStateView.READY
+        title: root.zoneState === "empty" ? qsTr("Zona no encontrada")
+                                         : qsTr("Zona no disponible")
+        message: root.errorMessage !== ""
+                 ? root.errorMessage
+                 : qsTr("El servicio Home Audio no está activo en esta instalación.")
+        retryAvailable: root.zoneState === "error" || root.zoneState === "empty"
+        onRetryRequested: root.refreshHeaderContext()
+
+        readyContent: Flickable {
+            id: viewport
+            anchors.fill: parent
+            anchors.margins: responsive.pageMargin
+            contentHeight: pageColumn.implicitHeight + MichiTheme.spacing.xxl
+            clip: true
+            boundsBehavior: Flickable.StopAtBounds
+            activeFocusOnTab: true
+
+            ColumnLayout {
+                id: pageColumn
+                width: viewport.width
+                spacing: MichiTheme.spacing.lg
+
+                RowLayout {
+                    Layout.fillWidth: true
+                    spacing: MichiTheme.spacing.md
+
+                    MichiIconButton {
+                        iconSource: "../../../icons/nav_back.svg"
+                        tooltipText: qsTr("Volver")
+                        accessibleName: tooltipText
+                        onClicked: {
+                            root.backClicked()
+                            if (typeof navigationBridge !== "undefined" && navigationBridge)
+                                navigationBridge.back()
+                        }
+                    }
+
+                    ColumnLayout {
+                        Layout.fillWidth: true
+                        spacing: MichiTheme.spacing.xxs
+
+                        Text {
+                            Layout.fillWidth: true
+                            text: root.zoneName || qsTr("Zona de audio")
+                            color: MichiTheme.colors.textPrimary
+                            font.pixelSize: MichiTheme.typography.pageTitleSize
+                            font.weight: MichiTheme.typography.weightBold
+                            elide: Text.ElideRight
+                        }
+
+                        Text {
+                            Layout.fillWidth: true
+                            text: root.zoneSource !== ""
+                                  ? qsTr("Fuente: %1").arg(root.zoneSource)
+                                  : qsTr("Sin fuente asignada")
+                            color: MichiTheme.colors.textSecondary
+                            font.pixelSize: MichiTheme.typography.bodySize
+                            elide: Text.ElideRight
+                        }
+                    }
+
+                    StatusBadge {
+                        text: root.zoneOnline
+                              ? (root.zoneStatus === "playing" ? qsTr("Reproduciendo")
+                                                              : qsTr("Conectada"))
+                              : qsTr("Sin conexión")
+                        kind: root.zoneOnline
+                              ? (root.zoneStatus === "playing" ? "active" : "success")
+                              : "disconnected"
+                    }
+
+                    MichiButton {
+                        text: qsTr("Renombrar")
+                        iconSource: "../../../icons/actions/edit.svg"
+                        variant: "secondary"
+                        onClicked: {
+                            renameField.text = root.zoneName
+                            renameDialog.open()
+                        }
+                    }
+                }
+
+                HeroMaterial {
+                    Layout.fillWidth: true
+                    Layout.preferredHeight: responsive.compact ? 176 : 148
+                    radius: MichiTheme.radius.lg
+                    showGlow: root.zoneStatus === "playing"
+
+                    RowLayout {
+                        anchors.fill: parent
+                        anchors.margins: MichiTheme.spacing.xl
+                        spacing: MichiTheme.spacing.xl
+
+                        Rectangle {
+                            Layout.preferredWidth: 72
+                            Layout.preferredHeight: 72
+                            radius: MichiTheme.radius.lg
+                            color: MichiTheme.colors.accentGlowSubtle
+                            border.width: MichiTheme.borderWidth
+                            border.color: MichiTheme.colors.accentSeparator
+
+                            MichiIcon {
+                                anchors.centerIn: parent
+                                iconKey: "home_audio"
+                                size: 32
+                                color: root.zoneStatus === "playing"
+                                       ? MichiTheme.colors.accentPrimary
+                                       : MichiTheme.colors.textSecondary
+                                accessibleName: ""
+                            }
+                        }
+
+                        ColumnLayout {
+                            Layout.fillWidth: true
+                            spacing: MichiTheme.spacing.xs
+
+                            Text {
+                                text: qsTr("Control de zona")
+                                color: MichiTheme.colors.textPrimary
+                                font.pixelSize: MichiTheme.typography.sectionTitleSize
+                                font.weight: MichiTheme.typography.weightSemiBold
+                            }
+
+                            Text {
+                                Layout.fillWidth: true
+                                text: qsTr("Ajusta el nivel, silencia o recupera la conexión sin abandonar esta vista.")
+                                color: MichiTheme.colors.textSecondary
+                                font.pixelSize: MichiTheme.typography.bodySize
+                                wrapMode: Text.WordWrap
+                            }
+                        }
+
+                        MichiButton {
+                            text: root.zoneMuted ? qsTr("Activar sonido") : qsTr("Silenciar")
+                            variant: root.zoneMuted ? "tonal" : "secondary"
+                            onClicked: {
+                                var nextMuted = !root.zoneMuted
+                                var result = root.ha.setZoneMute(root.zoneId, nextMuted)
+                                if (!root._showOperationError(result, qsTr("No se pudo cambiar el silencio."))) {
+                                    root.zoneMuted = nextMuted
+                                    root.muteToggled(root.zoneId, nextMuted)
+                                }
+                            }
+                        }
+
+                        MichiButton {
+                            visible: !root.zoneOnline
+                            text: qsTr("Reconectar")
+                            onClicked: {
+                                root.reconnectClicked(root.zoneId)
+                                root.refreshHeaderContext()
+                            }
+                        }
+                    }
+                }
+
+                GridLayout {
+                    Layout.fillWidth: true
+                    columns: responsive.compact ? 1 : 2
+                    columnSpacing: MichiTheme.spacing.lg
+                    rowSpacing: MichiTheme.spacing.lg
+
+                    MichiCard {
+                        Layout.fillWidth: true
+                        Layout.preferredHeight: 216
+                        title: qsTr("Volumen")
+                        subtitle: qsTr("Nivel independiente de esta zona")
+                        variant: "glass"
+
+                        ColumnLayout {
+                            width: parent.width
+                            spacing: MichiTheme.spacing.md
+
+                            RowLayout {
+                                Layout.fillWidth: true
+                                Text {
+                                    Layout.fillWidth: true
+                                    text: root.zoneMuted ? qsTr("Silenciada") : qsTr("Nivel actual")
+                                    color: MichiTheme.colors.textSecondary
+                                    font.pixelSize: MichiTheme.typography.bodySize
+                                }
+                                Text {
+                                    text: root.zoneVolume + "%"
+                                    color: MichiTheme.colors.accentPrimary
+                                    font.pixelSize: MichiTheme.typography.cardTitleSize
+                                    font.weight: MichiTheme.typography.weightBold
+                                }
+                            }
+
+                            MichiSlider {
+                                Layout.fillWidth: true
+                                from: 0
+                                to: 100
+                                stepSize: 1
+                                value: root.zoneVolume
+                                enabled: !root.zoneMuted && root.zoneOnline
+                                accessibleName: qsTr("Volumen de %1").arg(root.zoneName)
+                                accessibleDescription: qsTr("%1 por ciento").arg(root.zoneVolume)
+                                onMoved: {
+                                    root.zoneVolume = Math.round(value)
+                                    var result = root.ha.setZoneVolume(root.zoneId,
+                                                                       root.zoneVolume / 100.0)
+                                    if (!root._showOperationError(result, qsTr("No se pudo ajustar el volumen.")))
+                                        root.zoneDetailVolumeChanged(root.zoneId,
+                                                                     root.zoneVolume / 100.0)
+                                }
+                            }
+                        }
+                    }
+
+                    MichiCard {
+                        Layout.fillWidth: true
+                        Layout.preferredHeight: 216
+                        title: qsTr("Fuente y sincronización")
+                        subtitle: qsTr("Origen activo y compensación de latencia")
+                        variant: "glass"
+
+                        ColumnLayout {
+                            width: parent.width
+                            spacing: MichiTheme.spacing.md
+
+                            MichiComboBox {
+                                Layout.fillWidth: true
+                                model: root.ha && root.ha.sources ? root.ha.sources : []
+                                textRole: "name"
+                                placeholderText: root.zoneSource !== ""
+                                                 ? root.zoneSource : qsTr("Seleccionar fuente")
+                                accessibleName: qsTr("Fuente de la zona")
+                                onActivated: function(index) {
+                                    var item = root.model && root.model[index] ? root.model[index] : null
+                                    var source = item ? (item.id || item.name || "") : ""
+                                    if (source === "")
+                                        return
+                                    var result = root.ha.setSource(source)
+                                    if (!root._showOperationError(result, qsTr("No se pudo cambiar la fuente."))) {
+                                        root.zoneSource = item.name || source
+                                        root.sourceChanged(root.zoneId, source)
+                                    }
+                                }
+                            }
+
+                            RowLayout {
+                                Layout.fillWidth: true
+                                Text {
+                                    Layout.fillWidth: true
+                                    text: qsTr("Latencia")
+                                    color: MichiTheme.colors.textSecondary
+                                    font.pixelSize: MichiTheme.typography.bodySize
+                                }
+                                Text {
+                                    text: root.zoneLatencyMs + " ms"
+                                    color: MichiTheme.colors.textPrimary
+                                    font.pixelSize: MichiTheme.typography.bodySize
+                                    font.weight: MichiTheme.typography.weightSemiBold
+                                }
+                            }
+
+                            MichiSlider {
+                                Layout.fillWidth: true
+                                from: 0
+                                to: 500
+                                stepSize: 5
+                                value: root.zoneLatencyMs
+                                accessibleName: qsTr("Latencia de %1").arg(root.zoneName)
+                                accessibleDescription: qsTr("%1 milisegundos").arg(root.zoneLatencyMs)
+                                onMoved: {
+                                    root.zoneLatencyMs = Math.round(value)
+                                    var result = root.ha.setLatency(root.zoneId, root.zoneLatencyMs)
+                                    root._showOperationError(
+                                        result, qsTr("No se pudo ajustar la latencia."))
+                                }
+                            }
+                        }
+                    }
+                }
+
+                RowLayout {
+                    Layout.fillWidth: true
+                    SectionHeader {
+                        Layout.fillWidth: true
+                        text: qsTr("Dispositivos de la zona")
+                    }
+                    StatusBadge {
+                        text: qsTr("%1 dispositivos").arg(root.zoneDevices.length)
+                        kind: "info"
+                    }
+                }
+
+                Flow {
+                    Layout.fillWidth: true
+                    spacing: MichiTheme.spacing.md
+
+                    Repeater {
+                        model: root.zoneDevices
+
+                        MichiCard {
+                            width: responsive.compact
+                                   ? parent.width
+                                   : Math.max(240, (parent.width - MichiTheme.spacing.md) / 2)
+                            height: 86
+                            title: typeof modelData === "object"
+                                   ? (modelData.name || modelData.id || qsTr("Dispositivo"))
+                                   : String(modelData)
+                            subtitle: typeof modelData === "object"
+                                      ? (modelData.type || modelData.state || qsTr("Receptor de audio"))
+                                      : qsTr("Receptor de audio")
+                            variant: "base"
+                        }
+                    }
+                }
+
+                MichiBanner {
+                    Layout.fillWidth: true
+                    visible: root.zoneDevices.length === 0
+                    message: qsTr("Esta zona no tiene dispositivos asociados.")
+                    kind: "info"
+                    dismissible: false
+                }
+
+                Rectangle {
+                    Layout.fillWidth: true
+                    Layout.preferredHeight: MichiTheme.borderWidth
+                    color: MichiTheme.colors.borderSubtle
+                }
+
+                RowLayout {
+                    Layout.fillWidth: true
+                    spacing: MichiTheme.spacing.sm
+
+                    MichiButton {
+                        text: qsTr("Agrupar")
+                        variant: "secondary"
+                        onClicked: {
+                            root.groupClicked(root.zoneId)
+                            if (typeof navigationBridge !== "undefined" && navigationBridge)
+                                navigationBridge.navigateWithParams(
+                                    "group_editor", { zoneId: root.zoneId })
+                        }
+                    }
+
+                    MichiButton {
+                        text: qsTr("Desagrupar")
+                        variant: "secondary"
+                        onClicked: {
+                            var result = root.ha.ungroupZone(root.zoneId)
+                            if (!root._showOperationError(result, qsTr("No se pudo desagrupar la zona.")))
+                                root.ungroupClicked(root.zoneId)
+                        }
+                    }
+
+                    Item { Layout.fillWidth: true }
+
+                    MichiButton {
+                        text: qsTr("Eliminar zona")
+                        iconSource: "../../../icons/actions/trash.svg"
+                        variant: "danger"
+                        onClicked: deleteDialog.open()
+                    }
+                }
+            }
+        }
+    }
+
+    QQC2.Dialog {
+        id: renameDialog
+        parent: root
+        anchors.centerIn: parent
+        width: Math.min(460, root.width - MichiTheme.spacing.xl * 2)
+        modal: true
+        title: qsTr("Renombrar zona")
+        standardButtons: QQC2.Dialog.Cancel | QQC2.Dialog.Save
+
+        contentItem: MichiTextField {
+            id: renameField
+            width: parent.width
+            label: qsTr("Nombre")
+            placeholderText: qsTr("Nombre de la zona")
+            maxLength: 80
+            accessibleName: qsTr("Nuevo nombre de la zona")
+        }
+
+        onAccepted: {
+            var name = renameField.text.trim()
+            if (name === "")
+                return
+            var result = root.ha.renameZone(root.zoneId, name)
+            if (!root._showOperationError(result, qsTr("No se pudo renombrar la zona."))) {
+                root.zoneName = name
+                root.renameRequested(root.zoneId, name)
+            }
+        }
+    }
+
+    QQC2.Dialog {
+        id: deleteDialog
+        parent: root
+        anchors.centerIn: parent
+        width: Math.min(460, root.width - MichiTheme.spacing.xl * 2)
+        modal: true
+        title: qsTr("Eliminar zona")
+        standardButtons: QQC2.Dialog.Cancel | QQC2.Dialog.Ok
+
+        contentItem: Text {
+            width: parent.width
+            text: qsTr("Se eliminará “%1” de la configuración Home Audio.").arg(root.zoneName)
+            color: MichiTheme.colors.textPrimary
+            font.pixelSize: MichiTheme.typography.bodySize
+            wrapMode: Text.WordWrap
+        }
+
+        onAccepted: {
+            var result = root.ha.deleteZone(root.zoneId)
+            if (!root._showOperationError(result, qsTr("No se pudo eliminar la zona."))) {
+                root.deleteRequested(root.zoneId)
+                if (typeof navigationBridge !== "undefined" && navigationBridge)
+                    navigationBridge.back()
+            }
+        }
+    }
+
+    Connections {
+        target: root.ha
+        ignoreUnknownSignals: true
+        function onStateChanged() {
+            if (root.zoneState === "ready") {
+                var zone = root._zoneForId(root.zoneId)
+                if (zone)
+                    root._applyZone(zone)
+            }
+        }
+    }
+
+    Component.onCompleted: {
+        if (root.zoneId !== "")
+            root.refreshHeaderContext()
+    }
+}
