import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"
import "../materials"

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
    property var contextPage: null

    readonly property bool hasContext: root.contextPage &&
                                       root.contextPage.headerContextEnabled === true
    readonly property bool contextSearchEnabled: root.hasContext &&
                                                 root.contextPage.headerSearchEnabled === true
    readonly property var contextViewModes: root.hasContext &&
                                            root.contextPage.headerViewModes
                                            ? root.contextPage.headerViewModes : []
    readonly property int contextCurrentView: root.hasContext &&
                                              root.contextPage.headerCurrentView !== undefined
                                              ? root.contextPage.headerCurrentView : 0
    readonly property bool contextFilterEnabled: root.hasContext &&
                                                 root.contextPage.headerFilterEnabled === true
    readonly property int contextFilterCount: root.hasContext &&
                                              root.contextPage.headerFilterCount !== undefined
                                              ? root.contextPage.headerFilterCount : 0
    readonly property bool contextRefreshEnabled: root.hasContext &&
                                                  root.contextPage.headerRefreshEnabled === true
    readonly property bool contextLoading: root.hasContext &&
                                           root.contextPage.headerLoading === true
    readonly property string contextStatusText: root.hasContext &&
                                                root.contextPage.headerStatusText
                                                ? root.contextPage.headerStatusText : ""
    readonly property string effectiveSearchPlaceholder: root.contextSearchEnabled &&
                                                         root.contextPage.headerSearchPlaceholder
                                                         ? root.contextPage.headerSearchPlaceholder
                                                         : qsTr("Buscar en Michi…")
    property bool _lastSearchWasContextual: false

    signal backClicked()
    signal forwardClicked()
    signal breadcrumbClicked(string route)
    signal searchRequested(string query, bool submitted)
    signal viewModeRequested(int index)
    signal filtersRequested()
    signal refreshRequested()

    function focusSearch() {
        searchField.forceInputFocus()
    }

    function syncContextSearch() {
        if (root.contextSearchEnabled) {
            var value = root.contextPage.headerSearchText !== undefined
                        ? root.contextPage.headerSearchText : ""
            searchField.setTextSilently(value)
        } else if (root._lastSearchWasContextual) {
            searchField.setTextSilently("")
        }
        root._lastSearchWasContextual = root.contextSearchEnabled
    }

    onContextPageChanged: Qt.callLater(root.syncContextSearch)

    height: MichiTheme.headerHeight

    Shortcut {
        sequence: StandardKey.Find
        context: Qt.ApplicationShortcut
        onActivated: root.focusSearch()
    }

    Shortcut {
        sequence: "F5"
        context: Qt.ApplicationShortcut
        enabled: root.contextRefreshEnabled && !root.contextLoading
        onActivated: root.refreshRequested()
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceChrome

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
                visible: breadcrumbs.length > 1 &&
                         (!root.hasContext || root.width >= 1050)

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
                visible: breadcrumbs.length <= 1 &&
                         (!root.hasContext || root.width >= 900)
                text: root.pageTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.bodySize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
                maximumLineCount: 1
                Layout.alignment: Qt.AlignVCenter
                Layout.fillWidth: !root.hasContext
                Layout.maximumWidth: root.hasContext ? 190 : 100000
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

            Text {
                visible: root.hasContext && root.contextStatusText !== "" &&
                         root.width >= 1060
                text: root.contextStatusText
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
                Layout.maximumWidth: 130
                Layout.alignment: Qt.AlignVCenter
            }

            HeaderViewSwitcher {
                id: viewSwitcher
                Layout.alignment: Qt.AlignVCenter
                modes: root.contextViewModes
                currentIndex: root.contextCurrentView
                loading: root.contextLoading
                onActivated: function(index) { root.viewModeRequested(index) }
            }

            MichiSearchField {
                id: searchField
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: root.hasContext
                                       ? Math.min(360, Math.max(210, root.width * 0.27))
                                       : Math.min(340, Math.max(220, root.width * 0.28))
                Layout.maximumWidth: root.hasContext ? 360 : 340
                placeholderText: root.effectiveSearchPlaceholder
                controlObjectName: "searchField"
                accessibleName: root.contextSearchEnabled
                                ? root.effectiveSearchPlaceholder
                                : qsTr("Buscar en Michi")
                accessibleDescription: root.contextSearchEnabled
                                       ? qsTr("Filtra la sección de biblioteca visible")
                                       : qsTr("Busca en todas las secciones de Michi")
                loading: root.contextLoading
                debounceMs: root.contextSearchEnabled ? 240 : 300
                onSearchTextChanged: function(query) {
                    root.searchRequested(query, false)
                }
                onSearchSubmitted: function(query) {
                    if (query.trim().length > 0)
                        root.searchRequested(query.trim(), true)
                }
                onClearRequested: root.searchRequested("", false)
            }

            MichiIconButton {
                id: filterButton
                visible: root.contextFilterEnabled
                iconSource: "../../icons/view/filter.svg"
                tooltipText: root.contextFilterCount > 0
                             ? qsTr("Filtros de Biblioteca (%1 activos)").arg(root.contextFilterCount)
                             : qsTr("Filtros de Biblioteca")
                accessibleName: tooltipText
                selected: root.contextFilterCount > 0
                symbolic: true
                enabled: !root.contextLoading
                onClicked: root.filtersRequested()
            }

            MichiIconButton {
                id: refreshButton
                visible: root.contextRefreshEnabled && root.width >= 980
                iconSource: "../../icons/refresh.svg"
                tooltipText: root.contextLoading
                             ? qsTr("Actualizando biblioteca…")
                             : qsTr("Actualizar sección (F5)")
                accessibleName: tooltipText
                symbolic: true
                enabled: !root.contextLoading
                onClicked: root.refreshRequested()

                RotationAnimator on rotation {
                    from: 0
                    to: 360
                    duration: 900
                    loops: Animation.Infinite
                    running: root.contextLoading
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

    Connections {
        target: root.contextPage
        ignoreUnknownSignals: true
        function onHeaderSearchTextChanged() {
            root.syncContextSearch()
        }
    }
}
