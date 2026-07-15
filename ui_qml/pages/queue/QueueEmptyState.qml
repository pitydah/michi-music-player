import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    id: root
    implicitHeight: 120
    objectName: "queue.emptyState"

    Accessible.role: Accessible.Grouping
    Accessible.name: "Cola vacía"

    ColumnLayout {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Cola vacía"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
            objectName: "queue.emptyState.title"
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Agrega canciones desde la Biblioteca, Álbumes o Artistas"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            objectName: "queue.emptyState.subtitle"
        }
    }
}
