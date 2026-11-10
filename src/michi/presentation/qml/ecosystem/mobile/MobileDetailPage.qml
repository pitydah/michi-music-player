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
    signal openInDevicesRequested(string canonicalId)
    signal diagnosticsRequested(string canonicalId)
    signal revokeRequested(string canonicalId)

    readonly property bool revoked: (mobile.homeMembership ?? "") === "revoked"
    readonly property bool trusted: (mobile.homeMembership ?? "") === "active"

    eyebrow: qsTr("MICHI MUSIC MOBILE")
    title: mobile.name ?? qsTr("Michi Music Mobile")
    subtitle: qsTr("Identidad, confianza, control y presencia. La música se sincroniza en Michi Devices.")
    iconName: "device"
    statusText: revoked ? qsTr("Revocado") : mobile.online ? qsTr("Conectado") : qsTr("Sin conexión")
    statusTone: revoked ? "error" : mobile.online ? "success" : "neutral"
    primaryAction: qsTr("Diagnóstico")
    readonly property string canonicalId: mobile.canonicalId ?? ""
    readonly property bool homeCanAdminister: (home.configured ?? false)
        && !(home.locked ?? true)
    primaryEnabled: false
    secondaryAction: qsTr("Abrir en Michi Devices")
    secondaryEnabled: false
    dangerVisible: !revoked && canonicalId.length > 0
    dangerEnabled: homeCanAdminister
    dangerMessage: qsTr("Revocar elimina su confianza en este Michi Home. Michi Devices y AirCat conservan sus propias reglas; la sincronización puede dejar de estar permitida si dependía de esta membresía.")
    dangerAction: qsTr("Revocar dispositivo")
    onPrimaryRequested: root.diagnosticsRequested(root.canonicalId)
    onSecondaryRequested: root.openInDevicesRequested(root.canonicalId)
    onDangerRequested: root.revokeRequested(root.canonicalId)

    MichiText {
        Layout.fillWidth: true
        visible: true
        text: qsTr("El diagnóstico por dispositivo y Michi Devices todavía no están disponibles como destinos dentro del Player.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: home.errorMessage.length > 0
        text: home.errorMessage
        role: "secondary"
        color: MichiPalette.error
        wrapMode: Text.WordWrap
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
