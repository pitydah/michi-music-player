import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Source Card"
    objectName: "sourceCard"
    focus: true
    id: root

    property int sourceId: 0
    property string sourceName: ""
    property string sourcePath: ""
    property string sourceType: "local"
    property bool sourceEnabled: true
    property string status: ""
    property int trackCount: 0
    property string lastIndexed: ""
    property bool scanning: false

    signal editRequested()
    signal removeRequested()
    signal toggleEnabled()
    signal scanRequested()

    width: parent.width; height: 64
    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.surfaceCard
    border.color: root.sourceEnabled ? "transparent" : MichiTheme.colors.borderSubtle
    border.width: root.sourceEnabled ? 0 : 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.md

        Rectangle {
            width: 40; height: 40; radius: MichiTheme.radius.md
            color: root.sourceEnabled ? MichiTheme.colors.accentSurface : MichiTheme.colors.surfaceHover

            Text {
                anchors.centerIn: parent
                text: root.sourceType === "local" ? "HD" : root.sourceType === "subsonic" ? "SV" : "SR"
                color: root.sourceEnabled ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightBold
            }
        }

        Column {
            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter

            RowLayout { spacing: MichiTheme.spacing.xs
                Text {
                    text: root.sourceName
                    color: root.sourceEnabled ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                }
                Text {
                    text: root.scanning ? "(Escaneando...)" : root.status
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
                text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: text !== ""
            }
        }

        Column {
            Layout.alignment: Qt.AlignVCenter
            spacing: MichiTheme.spacing.xs

            MichiButton {
                Accessible.role: Accessible.Button

                activeFocusOnTab: true

                text: root.sourceEnabled ? "Desactivar" : "Activar"
                variant: "ghost"; height: 24
                onClicked: root.toggleEnabled()
            }

            RowLayout { spacing: MichiTheme.spacing.xs
                MichiButton { text: "Editar"; variant: "ghost"; height: 24; onClicked: root.editRequested() }
                MichiButton { text: root.scanning ? "..." : "Escanear"; variant: "ghost"; height: 24; enabled: !root.scanning; onClicked: root.scanRequested() }
                MichiButton { text: "Eliminar"; variant: "ghost"; height: 24; onClicked: root.removeRequested() }
            }
        }
    }
}
