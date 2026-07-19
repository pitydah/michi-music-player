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
    property var breadcrumbs: []
    property var mainWindow: null

    signal backClicked()
    signal forwardClicked()
    signal breadcrumbClicked(string route)
    signal searchRequested(string query, bool submitted)

    function focusSearch() {
        searchField.forceInputFocus()
    }

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

            RowLayout {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: Math.min(340, implicitWidth)
                spacing: 0
                visible: breadcrumbs.length > 1

                Repeater {
                    model: breadcrumbs
                    delegate: RowLayout {
                        spacing: MichiTheme.spacing.xs

                        Text {
                            text: modelData.title
                            color: index === breadcrumbs.length - 1
                                ? MichiTheme.colors.textPrimary
                                : MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: index === breadcrumbs.length - 1
                                         ? MichiTheme.typography.weightSemiBold
                                         : MichiTheme.typography.weightNormal
                            elide: Text.ElideRight
                            maximumLineCount: 1
                            Layout.maximumWidth: index === breadcrumbs.length - 1 ? 200 : 120

                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -4
                                cursorShape: index < breadcrumbs.length - 1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                enabled: index < breadcrumbs.length - 1
                                activeFocusOnTab: enabled
                                Accessible.role: Accessible.Button
                                Accessible.name: qsTr("Ir a ") + modelData.title
                                onClicked: {
                                    if (index < breadcrumbs.length - 1) {
                                        root.breadcrumbClicked(modelData.route)
                                    }
                                }
                                Keys.onReturnPressed: if (enabled) root.breadcrumbClicked(modelData.route)
                                Keys.onSpacePressed: if (enabled) root.breadcrumbClicked(modelData.route)
                            }
                        }

                        Text {
                            text: "/"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            font.weight: MichiTheme.typography.weightNormal
                            opacity: 0.4
                            visible: index < breadcrumbs.length - 1
                        }
                    }
                }
            }

            Text {
                visible: breadcrumbs.length <= 1
                text: root.pageTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
                maximumLineCount: 1
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: true
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
                controlObjectName: "searchField"
                accessibleName: qsTr("Buscar en Michi")
                debounceMs: 300
                onSearchTextChanged: function(query) {
                    if (query.length >= 2)
                        root.searchRequested(query, false)
                }
                onSearchSubmitted: function(query) {
                    if (query.trim().length > 0)
                        root.searchRequested(query.trim(), true)
                }
            }

            MichiIconButton {
                id: themeBtn
                controlObjectName: "headerThemeToggle"
                iconSource: MichiTheme.darkMode ? "../../icons/theme_sun.svg" : "../../icons/theme_moon.svg"
                tooltipText: MichiTheme.darkMode ? qsTr("Modo claro") : qsTr("Modo oscuro")
                accessibleName: tooltipText
                onClicked: {
                    var dark = !MichiTheme.darkMode
                    MichiTheme.setDarkMode(dark)
                    if (typeof themeBridge !== "undefined" && themeBridge)
                        themeBridge.darkMode = dark
                }
            }
        }
    }

    Component.onCompleted: {
        if (typeof themeBridge !== "undefined" && themeBridge)
            MichiTheme.setDarkMode(themeBridge.darkMode)
    }

    Connections {
        target: typeof themeBridge !== "undefined" ? themeBridge : null
        function onThemeChanged() { MichiTheme.setDarkMode(themeBridge.darkMode) }
    }
}
