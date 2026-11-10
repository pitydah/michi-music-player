import QtQuick
import QtQuick.Layouts
import ".."
import "../../controls"
import "../../primitives"
import "../../theme"

EcosystemDetailShell {
    id: root
    objectName: "ecosystemDiagnosticsPage"
    signal navigationRequested(string routeId)
    eyebrow: qsTr("SALUD Y RECUPERACIÓN")
    title: qsTr("Ecosystem Doctor")
    subtitle: qsTr("Incidencias comprobadas y recuperación segura, sin cambios automáticos.")
    iconName: "heart"
    statusText: ecosystemOperations.doctor.state === "healthy" ? qsTr("Sin incidencias")
        : ecosystemOperations.doctor.state === "unknown" ? qsTr("Sin datos") : qsTr("Revisar")
    statusTone: ecosystemOperations.doctor.state === "healthy" ? "success" : "warning"
    onBackRequested: root.navigationRequested("ecosystem")
    Component.onCompleted: ecosystemOperations.viewDiagnostics()

    MichiButton {
        text: qsTr("Exportar informe de soporte")
        variant: "ghost"
        visible: ecosystemOperations.supportExportAvailable
        enabled: !ecosystemOperations.busy
        onClicked: ecosystemOperations.exportSupport()
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.lastErrorText.length > 0
        text: ecosystemOperations.lastErrorText
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.auditWarningText.length > 0
        text: ecosystemOperations.auditWarningText
        role: "secondary"
        wrapMode: Text.WordWrap
    }
    MichiText {
        Layout.fillWidth: true
        text: qsTr("Historial local de operaciones (códigos sin datos sensibles)")
        role: "section"
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: ecosystemOperations.events
        delegate: MichiText {
            required property var modelData
            Layout.fillWidth: true
            text: modelData.code + " · " + new Date(modelData.timestamp * 1000).toLocaleString()
            role: "secondary"
        }
    }
    MichiText {
        Layout.fillWidth: true
        visible: ecosystemOperations.issues.length === 0
        text: ecosystemOperations.doctor.state === "unknown"
            ? qsTr("Todavía no hay suficientes observaciones para evaluar el sistema.")
            : qsTr("No hay incidencias activas según los datos disponibles.")
        role: "secondary"
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: ecosystemOperations.issues
        delegate: MichiGlassSurface {
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: issueContent.implicitHeight + 2 * contentPadding
            elevation: "subtle"
            accented: modelData.severity === "error"
            accentColor: modelData.severity === "error" ? MichiPalette.error : MichiPalette.auroraBlue
            ColumnLayout {
                id: issueContent
                anchors.fill: parent
                spacing: MichiSpacing.md
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.title
                    role: "section"
                    wrapMode: Text.WordWrap
                }
                MichiText {
                    Layout.fillWidth: true
                    text: modelData.detail
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    MichiText { text: modelData.code.split(":")[0]; role: "technical" }
                    Item { Layout.fillWidth: true }
                    MichiButton {
                        text: modelData.action
                        variant: "ghost"
                        onClicked: root.navigationRequested(modelData.route)
                    }
                }
            }
        }
    }
}
