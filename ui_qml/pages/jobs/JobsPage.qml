import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Centro de trabajos"
    objectName: "jobsPage"
    focus: true
    id: root

    property var bridge: typeof jobBridge !== "undefined" ? jobBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var jobListModel: null

    Component.onCompleted: {
        if (root.bridge && root.bridge.jobModel)
            root.jobListModel = root.bridge.jobModel
        // Connect to job changes for notifications (only on new failures)
        if (root.bridge && root.notif) {
            var _lastFailed = 0
            root.bridge.jobsChanged.connect(function() {
                var failed = root.bridge.failedCount
                if (failed > _lastFailed && root.notif.showMessage) {
                    var newFails = failed - _lastFailed
                    root.notif.showMessage(newFails + " trabajo(s) fallaron", "warning")
                }
                _lastFailed = failed
            })
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

        // Header
        RowLayout {
            Layout.fillWidth: true
            Text { text: qsTr("Centro de trabajos"); font.pixelSize: MichiTheme.typography.pageTitleSize; color: MichiTheme.colors.textPrimary; font.weight: MichiTheme.typography.weightSemiBold }
            Item { Layout.fillWidth: true }
            Text { text: root.bridge ? root.bridge.activeCount + " activos" : ""; color: MichiTheme.colors.textSecondary; visible: root.bridge && root.bridge.activeCount > 0 }
            MichiButton { text: qsTr("Limpiar completados"); variant: "ghost"; onClicked: { if (root.bridge) root.bridge.clearCompleted() } }
        }

        Text {
            text: qsTr("Trabajos en segundo plano: conversiones, análisis, sincronización y escaneo.")
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
            Layout.fillWidth: true; wrapMode: Text.WordWrap
        }

        // Job list
        ListView {
            Accessible.role: Accessible.List
            Accessible.name: "Lista de trabajos"
            activeFocusOnTab: true
            focusPolicy: Qt.StrongFocus
            id: jobList; Layout.fillWidth: true; Layout.fillHeight: true
            model: root.jobListModel ? root.jobListModel : (root.bridge ? root.bridge.jobs : [])
            clip: true; spacing: 4; boundsBehavior: Flickable.StopAtBounds

            delegate: GlassMaterial {
                width: jobList.width; height: 64; radius: MichiTheme.radius.sm; variant: "base"

                RowLayout {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                    // Status indicator
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: {
                            var s = model.state || model.status || ""
                            if (s === "completed" || s === "succeeded") return MichiTheme.colors.success
                            if (s === "failed" || s === "error") return MichiTheme.colors.error
                            if (s === "running" || s === "processing") return MichiTheme.colors.accentBlue
                            if (s === "cancelled") return MichiTheme.colors.textMuted
                            return MichiTheme.colors.warning
                        }
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Info
                    Column {
                        Layout.fillWidth: true; spacing: 2
                        Text {
                            text: model.title || model.name || model.type || "Trabajo"
                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightMedium; elide: Text.ElideRight; width: parent.width
                        }
                        Text {
                            text: {
                                var s = model.state || model.status || ""
                                var p = model.progress || 0
                                var msg = model.message || model.error || ""
                                if (s === "completed" || s === "succeeded") return qsTr("Completado")
                                if (s === "failed") return qsTr("Error: %1").arg(msg)
                                if (s === "cancelled") return qsTr("Cancelado")
                                if (s === "running" || s === "processing") return qsTr("En progreso: %1%").arg(Math.round(p))
                                return s || qsTr("Pendiente")
                            }
                            color: {
                                var s = model.state || model.status || ""
                                if (s === "failed") return MichiTheme.colors.error
                                if (s === "completed") return MichiTheme.colors.success
                                return MichiTheme.colors.textSecondary
                            }
                            font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; width: parent.width
                        }
                    }

                    // Progress bar
                    MichiProgressBar {
                        value: model.progress || 0; from: 0; to: 100
                        implicitWidth: 80; implicitHeight: 6
                        visible: (model.state || model.status) === "running" || (model.state || model.status) === "processing"
                    }

                    // Cancel button
                    MichiButton {
                        text: qsTr("Cancelar"); variant: "ghost"; implicitWidth: 70; implicitHeight: 28
                        visible: (model.state || model.status) === "running" || (model.state || model.status) === "processing" || (model.state || model.status) === "queued"
                        onClicked: {
                            if (root.bridge) {
                                var jid = model.job_id !== undefined ? model.job_id : model.id
                                root.bridge.cancelJob(jid)
                            }
                        }
                        Accessible.name: "Cancelar trabajo"
                    }

                    // Retry button
                    MichiButton {
                        text: qsTr("Reintentar"); variant: "ghost"; implicitWidth: 70; implicitHeight: 28
                        visible: (model.state || model.status) === "failed"
                        onClicked: {
                            if (root.bridge) {
                                var jid = model.job_id !== undefined ? model.job_id : model.id
                                root.bridge.retryJob(jid)
                            }
                        }
                        Accessible.name: "Reintentar trabajo"
                    }
                }
            }
        }

        // Empty state
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: jobList.count === 0
            Column {
                anchors.centerIn: parent; spacing: MichiTheme.spacing.md
                Text { text: qsTr("No hay trabajos activos"); anchors.horizontalCenter: parent.horizontalCenter; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize }
                Text { text: qsTr("Los trabajos de conversión, análisis y sincronización aparecerán aquí."); anchors.horizontalCenter: parent.horizontalCenter; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; width: 300; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
            }
        }
    }
}
