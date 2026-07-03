import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property string pageTitle: "Inicio"

    height: MichiTheme.headerHeight

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceToolbar

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: MichiTheme.borderWidth
            color: MichiTheme.colors.borderSubtle
        }

        Row {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.xl
            anchors.rightMargin: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.sm

                Text {
                    text: root.pageTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
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
