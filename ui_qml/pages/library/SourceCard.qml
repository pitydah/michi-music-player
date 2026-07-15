import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Rectangle {
    id: root

    property int sourceId: 0
    property string sourceName: ""
    property string sourcePath: ""
    property string sourceType: "local"
    property bool enabled: true
    property string status: ""
    property int trackCount: 0
    property string lastIndexed: ""
    property bool scanning: false
    property string scanProgress: ""
    property int priority: 0
    property bool watchMode: false
    property int exclusionCount: 0

    signal editRequested()
    signal removeRequested()
    signal toggleEnabled(bool enable)
    signal scanRequested()
    signal cancelScanRequested()
    signal priorityChanged(int newPriority)
    signal watchModeToggled(bool enable)
    signal exclusionsRequested()

    width: parent.width; height: 64
    radius: MichiTheme.radiusSm
    color: MichiTheme.colors.surfaceCard
    border.color: root.enabled ? "transparent" : MichiTheme.colors.borderSubtle
    border.width: root.enabled ? 0 : 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.md

        Rectangle {
            width: 40; height: 40; radius: MichiTheme.radiusSm
            color: root.enabled ? MichiTheme.colors.accentSurface : MichiTheme.colors.surfaceHover

            Text {
                anchors.centerIn: parent
                text: root.sourceType === "local" ? "HD" : root.sourceType === "subsonic" ? "SV" : "SR"
                color: root.enabled ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightBold
            }
        }

        Column {
            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter

            RowLayout { spacing: MichiTheme.spacing.xs
                Text {
                    text: root.sourceName
                    color: root.enabled ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                }
                Text {
                    text: root.scanning ? (root.scanProgress || "Escaneando...") : root.status
                    color: root.scanning ? MichiTheme.colors.accentBlue :
                           root.status === "error" ? MichiTheme.colors.error :
                           root.status === "offline" ? MichiTheme.colors.warning : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: text !== ""
                }
            }

            Text {
                text: root.sourcePath
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                elide: Text.ElideMiddle; width: parent.width
            }

            Text {
                text: root.trackCount > 0 ? root.trackCount + " canciones" +
                      (root.exclusionCount > 0 ? " · " + root.exclusionCount + " exclusiones" : "") : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: text !== ""
            }

            Text {
                text: "Prioridad: " + root.priority + (root.watchMode ? " · Watch" : "")
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: true
            }
        }

        Column {
            Layout.alignment: Qt.AlignVCenter
            spacing: MichiTheme.spacing.xs

            MichiButton {
                text: root.enabled ? "Desactivar" : "Activar"
                variant: "ghost"; height: 24
                onClicked: root.toggleEnabled(!root.enabled)
            }

            RowLayout { spacing: MichiTheme.spacing.xs
                MichiButton { text: "Editar"; variant: "ghost"; height: 24; onClicked: root.editRequested() }
                MichiButton { text: root.scanning ? "Detener" : "Escanear"; variant: "ghost"; height: 24
                    onClicked: root.scanning ? root.cancelScanRequested() : root.scanRequested()
                }
                MichiButton { text: "Excluir"; variant: "ghost"; height: 24; onClicked: root.exclusionsRequested() }
                MichiButton { text: "Eliminar"; variant: "ghost"; height: 24; onClicked: root.removeRequested() }
            }
        }
    }
}
