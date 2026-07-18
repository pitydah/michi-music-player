import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue Empty State"
    objectName: "queueEmptyState_control"
    focus: true
    implicitHeight: 120

    ColumnLayout {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Cola vacía")
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Agrega canciones desde la Biblioteca, Álbumes o Artistas")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }
    }
}
