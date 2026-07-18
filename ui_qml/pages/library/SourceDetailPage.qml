import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Source Detail"
    objectName: "sourceDetailPage"
    focus: true
    id: root

    property int sourceId: 0
    property string sourceName: ""
    property var bridge: null
    property var _detail: ({})

    signal backRequested()

    function loadDetail(id) {
        sourceId = id
        if (root.bridge && root.bridge.getSourceDetail) {
            root._detail = root.bridge.getSourceDetail(id) || {}
            sourceName = root._detail.name || ""
        }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: MichiTheme.spacing.lg
        anchors.margins: MichiTheme.spacing.xl

        MichiButton { text: qsTr("← Volver a fuentes"); variant: "ghost"; onClicked: root.backRequested() }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 120; radius: MichiTheme.radius.sm
            color: MichiTheme.colors.surfaceCard

            Column {
                anchors.centerIn: parent; spacing: MichiTheme.spacing.sm

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.sourceName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: MichiTheme.spacing.md

                    Column { spacing: 2
                        Text { text: qsTr("Estado"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: root._detail.status || "desconocido"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                    }
                    Column { spacing: 2
                        Text { text: qsTr("Canciones"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: (root._detail.track_count || 0).toString(); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                    }
                    Column { spacing: 2
                        Text { text: qsTr("Último indexado"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                        Text { text: root._detail.last_indexed || "nunca"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
                    }
                }
            }
        }

        SectionHeader { text: qsTr("Acciones"); width: parent.width }

        RowLayout { spacing: MichiTheme.spacing.sm
            MichiButton { text: qsTr("Escanear ahora"); variant: "primary"; onClicked: { if (root.bridge && root.bridge.scanSource) root.bridge.scanSource(root.sourceId) } }
            MichiButton { text: qsTr("Cancelar escaneo"); variant: "ghost"; onClicked: { if (root.bridge && root.bridge.cancelScan) root.bridge.cancelScan(root.sourceId) } }
            MichiButton { text: qsTr("Reescanear completo"); variant: "ghost"; onClicked: { if (root.bridge && root.bridge.rescanSource) root.bridge.rescanSource(root.sourceId) } }
        }

        SectionHeader { text: qsTr("Configuración"); width: parent.width }

        GridLayout {
            columns: 2; columnSpacing: MichiTheme.spacing.lg; rowSpacing: MichiTheme.spacing.sm

            Text { text: qsTr("Ruta"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: root._detail.path || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

            Text { text: qsTr("Tipo"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: root._detail.source_type || "local"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

            Text { text: qsTr("Prioridad"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: (root._detail.priority || 0).toString(); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }

            Text { text: qsTr("Watch mode"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
            Text { text: root._detail.watch_mode ? "Activo" : qsTr("Inactivo"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize }
        }
    }
}
