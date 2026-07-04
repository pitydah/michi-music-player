import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var diag: typeof diagnosticsBridge !== "undefined" ? diagnosticsBridge : null

    function routeEnter(route) {
        if (root.diag) root.diag.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Diagnóstico"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.diag ? root.diag.checks : []

                GlassMaterial {
                    width: parent.width; height: 36; radius: MichiTheme.radiusSm
                    variant: modelData.ok ? "base" : "danger"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: 30; text: modelData.ok ? "[OK]" : "[--]"; color: modelData.ok ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.35; text: modelData.key || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.50; text: modelData.value || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { text: "Refrescar"; variant: "primary"; onClicked: { if (root.diag) root.diag.refresh() } }
                MichiButton { text: "Copiar diagnóstico"; variant: "ghost"; onClicked: { if (root.diag) root.diag.copyDiagnostics() } }
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
