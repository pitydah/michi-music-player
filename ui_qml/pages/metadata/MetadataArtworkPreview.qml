import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../../theme"

Item {
    id: root

    property string artworkStatus: ""
    property string coverKey: ""

    implicitHeight: 120

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusSm
        color: Qt.rgba(1.0, 1.0, 1.0, 0.02)

        Row {
            anchors.centerIn: parent
            spacing: MichiTheme.spacing.lg

            Rectangle {
                width: 80
                height: 80
                radius: MichiTheme.radiusXs
                color: Qt.rgba(1.0, 1.0, 1.0, 0.03)
                clip: true

                CoverBridge {
                    anchors.fill: parent
                    coverKey: root.coverKey
                }
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    text: "Carátula"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.artworkStatus || "Sin carátula"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }
    }
}
