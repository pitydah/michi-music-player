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
    property var mobile: ({})
    signal openInDevicesRequested(string michiId)
    signal diagnosticsRequested(string michiId)
    signal revokeRequested(string michiId)

    readonly property bool revoked: (mobile.homeMembership ?? "") === "revoked"
    readonly property bool trusted: (mobile.homeMembership ?? "") === "active"

    eyebrow: qsTr("MICHI MUSIC MOBILE")
    title: mobile.name ?? qsTr("Michi Music Mobile")
    subtitle: qsTr("Identidad, confianza, control y presencia. La música se sincroniza en Michi Devices.")
    iconName: "device"
    statusText: revoked ? qsTr("Revocado") : mobile.online ? qsTr("Conectado") : qsTr("Sin conexión")
    statusTone: revoked ? "error" : mobile.online ? "success" : "neutral"
    primaryAction: qsTr("Diagnóstico")
    primaryEnabled: (mobile.michiId ?? "").length > 0
    secondaryAction: qsTr("Abrir en Michi Devices")
    secondaryEnabled: trusted && (mobile.michiId ?? "").length > 0
    dangerVisible: !revoked && (mobile.michiId ?? "").length > 0
    dangerMessage: qsTr("Revocar elimina su confianza en este Michi Home. La sincronización AirCat dejará de estar permitida.")
    dangerAction: qsTr("Revocar dispositivo")
    onPrimaryRequested: root.diagnosticsRequested(mobile.michiId ?? "")
    onSecondaryRequested: root.openInDevicesRequested(mobile.michiId ?? "")
    onDangerRequested: root.revokeRequested(mobile.michiId ?? "")

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout1.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout1
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Identidad y confianza"); role: "section" }
            EcosystemStatusRow { label: qsTr("Michi ID"); status: mobile.michiId ?? "—" }
            EcosystemStatusRow { label: qsTr("Michi Home"); status: mobile.homeMembership ?? "—" }
            EcosystemStatusRow { label: qsTr("Versión"); status: mobile.version ?? "—" }
        }
    }

    MichiGlassSurface {
        implicitHeight: michiDetailsLayout2.implicitHeight + 2 * contentPadding
        Layout.fillWidth: true
        elevation: "subtle"
        contentPadding: MichiSpacing.lg
        ColumnLayout {
            id: michiDetailsLayout2
            anchors.fill: parent
            spacing: MichiSpacing.md
            MichiText { text: qsTr("Capacidades y permisos"); role: "section" }
            EcosystemStatusRow {
                label: qsTr("Control remoto")
                status: (mobile.capabilities ?? []).indexOf("remote_controller") >= 0 ? qsTr("Permitido") : qsTr("No disponible")
            }
            EcosystemStatusRow {
                label: qsTr("Playback endpoint")
                status: (mobile.capabilities ?? []).indexOf("playback_endpoint") >= 0 ? qsTr("Disponible") : qsTr("No disponible")
            }
            EcosystemStatusRow {
                label: qsTr("AirCat")
                status: (mobile.capabilities ?? []).indexOf("aircat") >= 0 ? qsTr("Disponible en Michi Devices") : qsTr("No disponible")
            }
        }
    }
}
