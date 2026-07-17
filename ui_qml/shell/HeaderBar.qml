import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"
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
    property var mainWindow: null

    signal backClicked()
    signal forwardClicked()
    signal breadcrumbClicked(string route)

    MichiResponsive { id: responsive; availableWidth: root.width }

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
            anchors.leftMargin: responsive.compact ? MichiTheme.spacing.md : MichiTheme.spacing.xl
            anchors.rightMargin: responsive.compact ? MichiTheme.spacing.md : MichiTheme.spacing.xl
            spacing: responsive.compact ? MichiTheme.spacing.sm : MichiTheme.spacing.md

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                MichiIconButton {
                    iconSource: "../../icons/nav_back.svg"
                    tooltipText: "Atrás"
                    btnSize: responsive.compact ? 24 : 28
                    enabled: root.canGoBack
                    onClicked: root.backClicked()
                    objectName: "backButton"
                    accessibleName: "Atrás"
                }

                MichiIconButton {
                    iconSource: "../../icons/nav_forward.svg"
                    tooltipText: "Adelante"
                    btnSize: responsive.compact ? 24 : 28
                    enabled: root.canGoForward
                    onClicked: root.forwardClicked()
                    objectName: "forwardButton"
                    accessibleName: "Adelante"
                }

                Item { width: MichiTheme.spacing.sm; height: 1 }

                Row {
                    id: breadcrumbRow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.xs
                    visible: root.routeHistory.length > 0

                    Repeater {
                        model: {
                            if (responsive.compact && root.routeHistory.length > 1)
                                return [root.routeHistory[root.routeHistory.length - 1]]
                            return root.routeHistory
                        }

                        delegate: Row {
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: typeof modelData === 'object' ? modelData.title : modelData
                                color: index < (responsive.compact ? 0 : root.routeHistory.length - 1) ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                font.weight: index < (responsive.compact ? 0 : root.routeHistory.length - 1) ? MichiTheme.typography.weightNormal : MichiTheme.typography.weightSemiBold
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                            }

                            Text {
                                text: "/"
                                color: MichiTheme.colors.textMeta
                                font.pixelSize: MichiTheme.typography.secondarySize
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                visible: index < (responsive.compact ? 0 : root.routeHistory.length - 1)
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                enabled: index < (responsive.compact ? 0 : root.routeHistory.length - 1)
                                onClicked: root.breadcrumbClicked(typeof modelData === 'object' ? modelData.route : modelData)
                            }
                        }
                    }
                }

                Text {
                    text: root.pageTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: responsive.compact ? MichiTheme.typography.bodySize : MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: root.routeHistory.length > 0 ? 0 : MichiTheme.spacing.sm
                    visible: root.routeHistory.length === 0 || routeHistory[root.routeHistory.length - 1] !== root.pageTitle
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }


            }

            Item { Layout.fillWidth: true; width: 1; height: 1 }

            SearchField {
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Buscar en Michi..."
                implicitWidth: responsive.compact ? Math.min(160, root.width * 0.2) : Math.min(280, root.width * 0.25)
                objectName: "searchField"
                Accessible.name: "Buscar en Michi"
            }

            MichiIconButton {
                objectName: "headerThemeToggle"
                tooltipText: MichiTheme.darkMode ? "Modo claro" : "Modo oscuro"
                Accessible.name: tooltipText
                onClicked: MichiTheme.setDarkMode(!MichiTheme.darkMode)
            }

            MichiIconButton {
                objectName: "headerMaximizeButton"
                tooltipText: root.mainWindow && root.mainWindow.visibility === Window.Maximized ? "Restaurar" : "Maximizar"
                Accessible.name: tooltipText
                onClicked: {
                    if (root.mainWindow && root.mainWindow.visibility === Window.Maximized)
                        root.mainWindow.showNormal()
                    else if (root.mainWindow)
                        root.mainWindow.showMaximized()
                }
            }
        }
    }
}
