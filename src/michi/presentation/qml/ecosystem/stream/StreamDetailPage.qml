import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    signal navigationRequested(string routeId)
    onBackRequested: root.navigationRequested("ecosystem")
    property var streamBridge: typeof streamDevice !== "undefined" ? streamDevice : null
    property var device: streamBridge ? streamBridge.selectedDevice : ({})
    signal factoryRecreateRequested(string michiId)
    readonly property var diagnostics: streamBridge ? streamBridge.lastDiagnostics : ({})
    readonly property var diagWifi: diagnostics.wifi ?? ({})
    readonly property var diagSession: diagnostics.session ?? ({})

    function diagBool(value) {
        return value === true ? qsTr("Sí") : value === false ? qsTr("No") : qsTr("Sin datos")
    }
    function diagText(value) {
        return value === undefined || value === null || value === "" ? qsTr("Sin datos") : String(value)
    }

    function action(id) {
        var actions = device.actions ?? []
        for (var i = 0; i < actions.length; ++i) {
            if (actions[i].id === id)
                return actions[i]
        }
        return { enabled: false, reason: qsTr("No disponible") }
    }

    eyebrow: qsTr("MICHI MUSIC STREAM")
    title: device.name ?? qsTr("Music Stream")
    subtitle: (device.version ?? "").length > 0 ? qsTr("Firmware %1").arg(device.version) : ""
    iconName: "audio-output"
    statusText: device.online ? qsTr("En línea") : qsTr("Sin conexión")
    statusTone: device.online ? "success" : "error"
    primaryAction: qsTr("Diagnóstico")
    primaryEnabled: !(streamBridge && streamBridge.busy) && (action("diagnostics").enabled ?? false)
    secondaryAction: qsTr("Actualizar firmware")
    secondaryEnabled: !(streamBridge && streamBridge.busy) && (action("firmware_update").enabled ?? false)
    dangerVisible: (device.michiId ?? "").length > 0
    dangerEnabled: action("factory_recreate").enabled ?? false
    dangerMessage: qsTr("Factory Recreate borra la instalación actual y vuelve a provisionar el dispositivo.")
    dangerAction: qsTr("Factory Recreate")

    onPrimaryRequested: if (streamBridge && device.canonicalId) streamBridge.diagnostics(device.canonicalId)
    onSecondaryRequested: if (streamBridge && device.canonicalId) streamBridge.updateFirmware(device.canonicalId)
    onDangerRequested: root.factoryRecreateRequested(device.michiId ?? "")

    MichiGlassSurface {
        implicitHeight: michiDiagnosticsLayout.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDiagnosticsLayout
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Diagnóstico del receptor"); role: "section" }
            MichiText {
                Layout.fillWidth: true
                visible: Object.keys(root.diagnostics).length === 0
                text: qsTr("Ejecuta «Diagnóstico» para consultar el receptor. Solo se muestran datos reales; el esquema de la extensión aún no está congelado.")
                role: "secondary"
                wrapMode: Text.WordWrap
            }
            EcosystemStatusRow {
                visible: Object.keys(root.diagnostics).length > 0
                label: qsTr("Wi-Fi")
                status: qsTr("Asociado: %1 · IPv4: %2")
                    .arg(root.diagBool(root.diagWifi.associated))
                    .arg(root.diagBool(root.diagWifi.ipv4_ready))
            }
            EcosystemStatusRow {
                visible: Object.keys(root.diagnostics).length > 0
                label: qsTr("Sesión")
                status: qsTr("%1 · revisión %2")
                    .arg(root.diagText(root.diagSession.state))
                    .arg(root.diagText(root.diagSession.metadata_revision))
            }
            EcosystemStatusRow {
                visible: Object.keys(root.diagnostics).length > 0
                label: qsTr("Paquetes aceptados")
                status: root.diagText(
                    root.diagnostics.packets_accepted ?? root.diagSession.packets_accepted)
            }
            EcosystemStatusRow {
                visible: Object.keys(root.diagnostics).length > 0
                label: qsTr("Firmware activo")
                status: root.diagText(
                    root.diagnostics.firmware_version ?? root.diagnostics.firmware)
            }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Estado del dispositivo"); role: "section" }
            EcosystemStatusRow { label: qsTr("Michi Home"); status: device.homeMembership ?? "—" }
            EcosystemStatusRow { label: qsTr("Última presencia"); status: (device.lastSeenMs ?? -1) >= 0 ? String(device.lastSeenMs) : qsTr("Sin datos") }
            EcosystemStatusRow { label: qsTr("Transportes"); status: (device.transports ?? []).join(", ") }
            MichiButton {
                visible: (device.canonicalId ?? "").length > 0
                text: qsTr("Reconfigurar red")
                variant: "ghost"
                enabled: !(streamBridge && streamBridge.busy) && (root.action("network_reprovision").enabled ?? false)
                onClicked: if (streamBridge) streamBridge.reprovisionNetwork(device.canonicalId)
            }
        }
    }
}
