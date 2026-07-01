import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property string pageTitle: "Inicio"

    height: 56

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.027, 0.039, 0.063, 0.92)

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.xl
            anchors.rightMargin: MichiSpacing.xl
            spacing: MichiSpacing.lg

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiSpacing.sm

                Text {
                    text: root.pageTitle
                    color: MichiColors.textPrimary
                    font.pixelSize: MichiTypography.pageTitleSize
                    font.weight: MichiTypography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                }

                StatusBadge {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Experimental"
                    kind: "experimental"
                }
            }

            Item { Layout.fillWidth: true; width: 1; height: 1 }

            SearchField {
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Buscar en Michi..."
                implicitWidth: Math.min(320, root.width * 0.25)
            }
        }
    }
}
