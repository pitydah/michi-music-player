import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root
    objectName: "diagnosticsPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Diagnóstico"

    property var diag: typeof diagnosticsBridge !== "undefined" ? diagnosticsBridge : null
    property int pageState: root.diag ? stateReady : stateError

    readonly property int stateLoading: 0
    readonly property int stateReady: 1
    readonly property int stateError: 2
    readonly property int stateEmpty: 3

    function routeEnter(route) {
        if (root.diag) root.diag.refresh()
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateLoading
        sourceComponent: LoadingState { title: qsTr("Cargando diagnóstico") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateError
        sourceComponent: ErrorState { message: qsTr("Diagnóstico no disponible") }
    }

    Loader {
        anchors.centerIn: parent
        active: root.pageState === root.stateEmpty
        sourceComponent: EmptyState { title: qsTr("Sin datos de diagnóstico") }
    }

    Flickable {
        visible: root.pageState === root.stateReady
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
                text: qsTr("Diagnóstico")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Repeater {
                model: root.diag ? root.diag.checks : []

                GlassMaterial {
                    width: parent.width; height: 36; radius: MichiTheme.radius.sm
                    variant: modelData.ok ? "base" : "danger"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: 30; text: modelData.ok ? "[OK]" : qsTr("[--]"); color: modelData.ok ? MichiTheme.colors.success : MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.35; text: modelData.key || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                        Text { width: parent.width * 0.50; text: modelData.value || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideRight }
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton { objectName: qsTr("refreshDiagnosticsButton"); text: "Refrescar"; variant: "primary"; onClicked: { if (root.diag) root.diag.refresh() } }
                MichiButton { objectName: qsTr("copyDiagnosticsButton"); text: "Copiar diagnóstico"; variant: "ghost"; onClicked: { if (root.diag) root.diag.copyDiagnostics() } }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column { anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: qsTr("Para depuración técnica"); kind: "info" }
                }
            }
        }
    }
}
