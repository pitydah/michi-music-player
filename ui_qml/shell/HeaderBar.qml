import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"

Item {
    id: root
    Accessible.role: Accessible.Pane
    Accessible.name: "Header Bar"
    objectName: "headerBar"
    focus: true

    property string pageTitle: "Inicio"
    property bool canGoBack: false
    property bool canGoForward: false
    property var routeHistory: []
    property var mainWindow: null

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

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.sm

            MichiIconButton {
                iconSource: "../../icons/nav_back.svg"
                tooltipText: qsTr("Atrás")
                enabled: root.canGoBack
                onClicked: root.backClicked()
                controlObjectName: "backButton"
                accessibleName: qsTr("Atrás")
            }

            MichiIconButton {
                iconSource: "../../icons/nav_forward.svg"
                tooltipText: qsTr("Adelante")
                enabled: root.canGoForward
                onClicked: root.forwardClicked()
                controlObjectName: "forwardButton"
                accessibleName: qsTr("Adelante")
            }

            Text {
                Layout.preferredWidth: Math.min(240, implicitWidth)
                Layout.maximumWidth: 240
                Layout.alignment: Qt.AlignVCenter
                text: root.pageTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Item {
                id: dragArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                Accessible.ignored: true

                DragHandler {
                    target: null
                    acceptedButtons: Qt.LeftButton
                    onActiveChanged: {
                        if (active && root.mainWindow && root.mainWindow.startSystemMove)
                            root.mainWindow.startSystemMove()
                    }
                }
            }

            MichiSearchField {
                id: searchField
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Math.min(340, Math.max(220, root.width * 0.28))
                Layout.maximumWidth: 340
                placeholderText: qsTr("Buscar en Michi...")
                objectName: "searchField"
                Accessible.name: qsTr("Buscar en Michi")
            }

            MichiIconButton {
                id: themeBtn
                controlObjectName: "headerThemeToggle"
                iconSource: MichiTheme.darkMode ? "../../icons/theme_sun.svg" : "../../icons/theme_moon.svg"
                tooltipText: MichiTheme.darkMode ? qsTr("Modo claro") : qsTr("Modo oscuro")
                accessibleName: tooltipText
                onClicked: MichiTheme.setDarkMode(!MichiTheme.darkMode)
            }
        }
    }
}
