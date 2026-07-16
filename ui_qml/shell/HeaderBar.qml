import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Header Bar"
    objectName: "headerBar"
    focus: true
    id: root

    property string pageTitle: "Inicio"
    property bool canGoBack: false
    property bool canGoForward: false
    property var routeHistory: []

    signal backClicked()
    signal forwardClicked()
    signal breadcrumbClicked(string route)

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
            spacing: MichiTheme.spacing.md

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                MichiIconButton {
                    iconText: "<"
                    tooltipText: "Atrás"
                    btnSize: 28
                    enabled: root.canGoBack
                    onClicked: root.backClicked()
                    Accessible.name: "Navegar atrás"
                }

                MichiIconButton {
                    iconText: ">"
                    tooltipText: "Adelante"
                    btnSize: 28
                    enabled: root.canGoForward
                    onClicked: root.forwardClicked()
                    Accessible.name: "Navegar adelante"
                }

                Text {
                    text: root.pageTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: MichiTheme.spacing.sm
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
                implicitWidth: Math.min(280, root.width * 0.25)
            }
        }
    }
}
