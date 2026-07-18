import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Source Scan Progress"
    objectName: "sourceScanProgress"
    focus: true
    id: root

    property string sourceName: ""
    property int progress: 0
    property int total: 0
    property int filesFound: 0
    property bool scanning: false
    property bool indeterminate: false

    width: parent.width; height: 48
    radius: MichiTheme.radius.sm
    color: MichiTheme.colors.surfaceCard
    visible: root.scanning

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.md

        Column {
            Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter
            spacing: 2

            RowLayout { spacing: MichiTheme.spacing.xs
                Text {
                    text: qsTr("Escaneando: ") + root.sourceName
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                }
                Text {
                    text: root.filesFound > 0 ? "(" + root.filesFound + " archivos)" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }
            }

            ProgressBar {
                Accessible.role: Accessible.ProgressBar

                Accessible.name: "Progreso de escaneo"

                Layout.fillWidth: true; height: 4
                from: 0; to: root.total > 0 ? root.total : 1
                value: root.indeterminate ? 0 : root.progress
                indeterminate: root.indeterminate
            }
        }

        MichiButton { text: qsTr("Cancelar"); variant: "ghost"; height: 24 }
    }
}
