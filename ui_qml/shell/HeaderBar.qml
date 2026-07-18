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

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: responsive.compact ? MichiTheme.spacing.md : MichiTheme.spacing.xl
            anchors.rightMargin: responsive.compact ? MichiTheme.spacing.md : MichiTheme.spacing.xl
            spacing: responsive.compact ? MichiTheme.spacing.sm : MichiTheme.spacing.md

            // Navegación (atrás/adelante + breadcrumbs)
            RowLayout {
                Layout.fillWidth: true
                width: 400
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

                // Breadcrumbs
                Row {
                    id: breadcrumbRow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.xs
                    visible: root.routeHistory.length > 0
                    width: 250
                    clip: true

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
                                elide: Text.ElideRight
                                width: 120
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

                // Título de página (solo si no está ya en breadcrumbs)
                Text {
                    text: root.pageTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: responsive.compact ? MichiTheme.typography.bodySize : MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: root.routeHistory.length > 0 ? 0 : MichiTheme.spacing.sm
                    visible: root.routeHistory.length === 0
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    width: 200
                }
            }

            // Espacio flexible
            Item { Layout.fillWidth: true; height: 1 }

            // Búsqueda
            SearchField {
                id: searchField
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Buscar en Michi..."
                implicitWidth: responsive.compact ? Math.min(160, root.width * 0.2) : Math.min(280, root.width * 0.25)
                objectName: "searchField"
                Accessible.name: "Buscar en Michi"
            }

            // Botón modo claro/oscuro
            MichiIconButton {
                id: themeBtn
                objectName: "headerThemeToggle"
                iconText: MichiTheme.darkMode ? "\u2600" : "\u263D"
                tooltipText: MichiTheme.darkMode ? "Modo claro" : "Modo oscuro"
                Accessible.name: tooltipText
                btnSize: 28
                onClicked: MichiTheme.setDarkMode(!MichiTheme.darkMode)
            }

            // Botón maximizar/restaurar
            MichiIconButton {
                id: maxBtn
                objectName: "headerMaximizeButton"
                iconText: root.mainWindow && root.mainWindow.visibility === Window.Maximized ? "\u25A1" : "\u25A2"
                tooltipText: root.mainWindow && root.mainWindow.visibility === Window.Maximized ? "Restaurar" : "Maximizar"
                Accessible.name: tooltipText
                btnSize: 28
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
