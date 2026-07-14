import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    implicitHeight: 120

    ColumnLayout {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Cola vacía"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightMedium
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "Agrega canciones desde la Biblioteca, Álbumes o Artistas"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
        }
    }
}
