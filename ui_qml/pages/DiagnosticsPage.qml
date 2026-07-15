import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var diag: typeof diagnosticsBridge !== "undefined" ? diagnosticsBridge : null

    objectName: "diagnostics.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Diagnóstico"
    Accessible.description: "Panel de diagnóstico del sistema"

    Keys.onEscapePressed: {
        root.diag && root.diag.refresh && root.diag.refresh()
    }

    function routeEnter(route) {
        if (root.diag) root.diag.refresh()
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        objectName: "diagnostics.flickable"

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg
            objectName: "diagnostics.column"

            Text {
                id: titleText
                text: "Diagnóstico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "diagnostics.title"
                Accessible.role: Accessible.Heading
                Accessible.name: "Diagnóstico"
            }

            Repeater {
                model: root.diag ? root.diag.checks : []

                GlassMaterial {
                    width: parent.width; height: 36; radius: MichiTheme.radiusSm
                    variant: modelData.ok ? "base" : "danger"
                    objectName: "diagnostics.check." + index
                    Accessible.name: modelData.key || "check"

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: 30; text: modelData.ok ? "[OK]" : "[--]"; color: modelData.ok ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; Accessible.name: modelData.ok ? "OK" : "Error" }
                        Text { width: parent.width * 0.35; text: modelData.key || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight; Accessible.name: modelData.key || "" }
                        Text { width: parent.width * 0.50; text: modelData.value || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight; Accessible.name: modelData.value || "" }
                    }
                }
            }

            Row {
                id: actionRow
                spacing: MichiTheme.spacing.sm
                objectName: "diagnostics.actions"

                MichiButton { id: refreshBtn; text: "Refrescar"; variant: "primary"; objectName: "diagnostics.refresh"; Accessible.name: "Refrescar diagnóstico"; onClicked: { if (root.diag) root.diag.refresh() } }
                MichiButton { id: copyBtn; text: "Copiar diagnóstico"; variant: "ghost"; objectName: "diagnostics.copy"; Accessible.name: "Copiar diagnóstico al portapapeles"; onClicked: { if (root.diag) root.diag.copyDiagnostics() } }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column { anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                    StatusBadge { text: "Para depuración técnica"; kind: "info" }
                }
            }
        }
    }
}
