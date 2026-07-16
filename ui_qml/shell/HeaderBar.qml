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
                    objectName: "backButton"
                    accessibleName: "Atrás"
                }

                MichiIconButton {
                    iconText: ">"
                    tooltipText: "Adelante"
                    btnSize: 28
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
                        model: root.routeHistory

                        delegate: Row {
                            spacing: MichiTheme.spacing.xs

                            Text {
                                text: modelData
                                color: index < root.routeHistory.length - 1 ? MichiTheme.colors.textMuted : MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.secondarySize
                                font.weight: index < root.routeHistory.length - 1 ? MichiTheme.typography.weightNormal : MichiTheme.typography.weightSemiBold
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "/"
                                color: MichiTheme.colors.textMeta
                                font.pixelSize: MichiTheme.typography.secondarySize
                                anchors.verticalCenter: parent.verticalCenter
                                visible: index < root.routeHistory.length - 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                enabled: index < root.routeHistory.length - 1
                                onClicked: root.breadcrumbClicked(modelData)
                            }
                        }
                    }
                }

                Text {
                    text: root.pageTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: root.routeHistory.length > 0 ? 0 : MichiTheme.spacing.sm
                    visible: root.routeHistory.length === 0 || routeHistory[root.routeHistory.length - 1] !== root.pageTitle
                }

                StatusBadge {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Experimental"
                    kind: "experimental"
                    objectName: "experimentalBadge"
                    Accessible.name: "Experimental"
                }
            }

            Item { Layout.fillWidth: true; width: 1; height: 1 }

            SearchField {
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: "Buscar en Michi..."
                implicitWidth: Math.min(280, root.width * 0.25)
                objectName: "searchField"
                Accessible.name: "Buscar en Michi"
            }
        }
    }
}
