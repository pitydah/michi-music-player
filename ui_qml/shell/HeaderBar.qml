import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property string pageTitle: "Inicio"
    property string routeTitle: "Inicio"
    property bool canGoBack: false
    property bool canGoForward: false

    signal backRequested()
    signal forwardRequested()

    height: MichiTheme.headerHeight

    objectName: "headerBar"
    Accessible.role: Accessible.Panel
    Accessible.name: "Barra superior"

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
            anchors.leftMargin: MichiTheme.spacing.sm
            anchors.rightMargin: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.sm

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2

                MichiIconButton {
                    iconText: ""
                    tooltipText: "Atrás"
                    btnSize: 32
                    enabled: root.canGoBack
                    objectName: "header.backButton"
                    Accessible.name: "Navegar atrás"
                    onClicked: root.backRequested()
                }

                MichiIconButton {
                    iconText: ""
                    tooltipText: "Adelante"
                    btnSize: 32
                    enabled: root.canGoForward
                    objectName: "header.forwardButton"
                    Accessible.name: "Navegar adelante"
                    onClicked: root.forwardRequested()
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.routeTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.name: "Título de página: " + root.routeTitle
            }

            StatusBadge {
                anchors.verticalCenter: parent.verticalCenter
                text: "Experimental"
                kind: "experimental"
                Accessible.name: "Versión experimental"
            }

            Item { width: 1; height: 1; Layout.fillWidth: true }

            SearchField {
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Buscar en Michi..."
                implicitWidth: Math.min(280, root.width * 0.25)
                objectName: "header.searchField"
                Accessible.name: "Búsqueda global"
            }
        }
    }
}
