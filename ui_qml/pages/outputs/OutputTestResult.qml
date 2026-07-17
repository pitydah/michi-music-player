import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Output Test Result"
    objectName: "outputTestResult"
    focus: true
    id: root

    property var testResult: null
    property bool testing: false

    implicitHeight: root.testing ? 80 : (root.testResult ? 120 : 0)

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radius.md
        variant: root.testResult && root.testResult.ok ? "base" : "status"

        Column {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.sm

            Text {
                text: root.testing ? "Probando perfil..." : (root.testResult ? (root.testResult.ok ? "Prueba exitosa" : "Prueba fallida") : "")
                color: root.testing ? MichiTheme.colors.textMuted : (root.testResult && root.testResult.ok ? MichiTheme.colors.success : MichiTheme.colors.error)
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: root.testResult && root.testResult.message ? root.testResult.message : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                anchors.horizontalCenter: parent.horizontalCenter
                visible: text !== ""
            }

            Row {
                spacing: MichiTheme.spacing.sm
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root.testResult && !root.testResult.ok && root.testResult.details

                Text {
                    text: "Detalles: " + (root.testResult.details || "")
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }
}
