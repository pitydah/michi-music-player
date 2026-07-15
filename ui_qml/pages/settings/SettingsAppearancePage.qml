import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    objectName: "settingsAppearancePage"
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var themeBridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de apariencia"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
        if (root.themeBridge && typeof root.themeBridge.applySetting === "function")
            root.themeBridge.applySetting(key, value)
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.appearance.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de apariencia"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Apariencia"
                    subtitle: "Tema, colores y disposición visual"
                }

                GlassCard {
                    id: colorsCard
                    Layout.fillWidth: true
                    title: "Colores"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Color de acento"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Color principal para elementos interactivos"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            RowLayout {
                                spacing: MichiTheme.spacing.sm

                                Repeater {
                                    model: [
                                        { color: "#8FB7FF", name: "Azul" },
                                        { color: "#A78BFA", name: "Morado" },
                                        { color: "#FF7A00", name: "Naranja" },
                                        { color: "#4ADE80", name: "Verde" },
                                        { color: "#F87171", name: "Rojo" },
                                        { color: "#F0F2F8", name: "Blanco" }
                                    ]

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: width / 2
                                        color: modelData.color
                                        border.width: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? 3 : 1
                                        border.color: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? MichiTheme.colors.textPrimary : MichiTheme.colors.borderCard

                                        Accessible.role: Accessible.Button
                                        Accessible.name: "Color de acento " + modelData.name

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root._saveValue("appearance/accent_color", modelData.color)
                                        }
                                    }
                                }
<<<<<<< Updated upstream
=======

                                Keys.onReturnPressed: {
                                    if (root.bridge) root.bridge.accentColor = modelData
                                }
                                Keys.onSpacePressed: {
                                    if (root.bridge) root.bridge.accentColor = modelData
                                }
                                focus: true
                                activeFocusOnTab: true
=======
    objectName: "settingsAppearancePage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var themeBridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de apariencia"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
        if (root.themeBridge && typeof root.themeBridge.applySetting === "function")
            root.themeBridge.applySetting(key, value)
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.appearance.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de apariencia"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Apariencia"
                    subtitle: "Tema, colores y disposición visual"
                }

                GlassCard {
                    id: colorsCard
                    Layout.fillWidth: true
                    title: "Colores"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Color de acento"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Color principal para elementos interactivos"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            RowLayout {
                                spacing: MichiTheme.spacing.sm

                                Repeater {
                                    model: [
                                        { color: "#8FB7FF", name: "Azul" },
                                        { color: "#A78BFA", name: "Morado" },
                                        { color: "#FF7A00", name: "Naranja" },
                                        { color: "#4ADE80", name: "Verde" },
                                        { color: "#F87171", name: "Rojo" },
                                        { color: "#F0F2F8", name: "Blanco" }
                                    ]

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: width / 2
                                        color: modelData.color
                                        border.width: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? 3 : 1
                                        border.color: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? MichiTheme.colors.textPrimary : MichiTheme.colors.borderCard

                                        Accessible.role: Accessible.Button
                                        Accessible.name: "Color de acento " + modelData.name

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root._saveValue("appearance/accent_color", modelData.color)
                                        }
                                    }
                                }
>>>>>>> Stashed changes
                            }
                        }
                    }
                }

                GlassCard {
                    id: typographyCard
                    Layout.fillWidth: true
                    title: "Tipografía"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Escala de fuente"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: fontScaleSlider.value + "%"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                            }

                            MichiSlider {
                                id: fontScaleSlider
                                objectName: "settings.appearance.fontScale"
                                implicitWidth: 200
                                from: 75
                                to: 150
                                value: root._loadValue("appearance/font_scale", 100)
                                stepSize: 5
                                accessibleName: "Escala de fuente"
                                onMoved: root._saveValue("appearance/font_scale", value)
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("appearance/font_scale", value)
                                }
                                Accessible.description: "Ajusta el tamaño de la fuente: " + value + "%"
=======
                                focus: true
                                activeFocusOnTab: true
=======
    objectName: "settingsAppearancePage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var themeBridge: typeof themeBridge !== "undefined" ? themeBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de apariencia"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
    }

    function _loadValue(key, fallback) {
        if (!root.bridge) return fallback
        var v = root.bridge.getValue(key)
        return v !== null && v !== undefined ? v : fallback
    }

    function _saveValue(key, value) {
        if (!root.bridge) return
        root.bridge.setValue(key, value)
        if (root.themeBridge && typeof root.themeBridge.applySetting === "function")
            root.themeBridge.applySetting(key, value)
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.appearance.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de apariencia"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Apariencia"
                    subtitle: "Tema, colores y disposición visual"
                }

                GlassCard {
                    id: colorsCard
                    Layout.fillWidth: true
                    title: "Colores"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Color de acento"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Color principal para elementos interactivos"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            RowLayout {
                                spacing: MichiTheme.spacing.sm

                                Repeater {
                                    model: [
                                        { color: "#8FB7FF", name: "Azul" },
                                        { color: "#A78BFA", name: "Morado" },
                                        { color: "#FF7A00", name: "Naranja" },
                                        { color: "#4ADE80", name: "Verde" },
                                        { color: "#F87171", name: "Rojo" },
                                        { color: "#F0F2F8", name: "Blanco" }
                                    ]

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: width / 2
                                        color: modelData.color
                                        border.width: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? 3 : 1
                                        border.color: root._loadValue("appearance/accent_color", "#8FB7FF") === modelData.color ? MichiTheme.colors.textPrimary : MichiTheme.colors.borderCard

                                        Accessible.role: Accessible.Button
                                        Accessible.name: "Color de acento " + modelData.name

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: root._saveValue("appearance/accent_color", modelData.color)
                                        }
                                    }
                                }
>>>>>>> Stashed changes
                            }
                        }
                    }
                }

                GlassCard {
<<<<<<< Updated upstream
                    id: visualCard
                    Layout.fillWidth: true
                    title: "Preferencias visuales"
                    interactive: false
=======
                    id: typographyCard
                    Layout.fillWidth: true
                    title: "Tipografía"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Escala de fuente"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: fontScaleSlider.value + "%"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
=======
>>>>>>> Stashed changes
                            }

                            MichiSlider {
                                id: fontScaleSlider
                                objectName: "settings.appearance.fontScale"
                                implicitWidth: 200
                                from: 75
                                to: 150
                                value: root._loadValue("appearance/font_scale", 100)
                                stepSize: 5
                                accessibleName: "Escala de fuente"
                                onMoved: root._saveValue("appearance/font_scale", value)
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("appearance/font_scale", value)
                                }
                                Accessible.description: "Ajusta el tamaño de la fuente: " + value + "%"
>>>>>>> origin/michi-qml-functional-wave
                            }
                        }
                    }
                }

<<<<<<< HEAD
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md
>>>>>>> Stashed changes

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Movimiento reducido"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: reducedMotion
                                objectName: "settings.appearance.reducedMotion"
                                checked: root._loadValue("appearance/reduced_motion", false)
                                onClicked: root._saveValue("appearance/reduced_motion", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Movimiento reducido"
                                Accessible.description: "Reducir animaciones y transiciones"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

<<<<<<< Updated upstream
=======
                        ComboBox {
                            id: fontScaleCombo
                            objectName: "settings.appearance.fontScale"
                            model: ["Pequeña", "Normal", "Grande", "Muy grande"]
                            currentIndex: 1
                            Accessible.name: "Escala de fuente"
                            KeyNavigation.tab: reduceMotionSwitch
=======
                GlassCard {
                    id: visualCard
                    Layout.fillWidth: true
                    title: "Preferencias visuales"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Movimiento reducido"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: reducedMotion
                                objectName: "settings.appearance.reducedMotion"
                                checked: root._loadValue("appearance/reduced_motion", false)
                                onClicked: root._saveValue("appearance/reduced_motion", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Movimiento reducido"
                                Accessible.description: "Reducir animaciones y transiciones"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Transparencia reducida"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: reducedTransparency
                                objectName: "settings.appearance.reducedTransparency"
                                checked: root._loadValue("appearance/reduced_transparency", false)
                                onClicked: root._saveValue("appearance/reduced_transparency", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Transparencia reducida"
                                Accessible.description: "Reducir efectos de transparencia y desenfoque"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Modo compacto"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: compactMode
                                objectName: "settings.appearance.compactMode"
                                checked: root._loadValue("interface/compact_mode", false)
                                onClicked: root._saveValue("interface/compact_mode", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Modo compacto"
                                Accessible.description: "Reducir espacios y márgenes"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Carátula como fondo"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: coverAsBackdrop
                                objectName: "settings.appearance.coverAsBackdrop"
                                checked: root._loadValue("appearance/cover_as_backdrop", false)
                                onClicked: root._saveValue("appearance/cover_as_backdrop", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Carátula como fondo"
                                Accessible.description: "Usar la carátula del álbum actual como fondo"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                GlassCard {
                    id: menuCard
                    Layout.fillWidth: true
                    title: "Barra de menú"
                    interactive: false
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md
>>>>>>> Stashed changes

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mostrar barra de menú"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: showMenubar
                                objectName: "settings.appearance.showMenubar"
                                checked: root._loadValue("interface/show_menubar", true)
                                onClicked: root._saveValue("interface/show_menubar", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mostrar barra de menú"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
                GlassCard {
                    id: menuCard
                    Layout.fillWidth: true
                    title: "Barra de menú"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mostrar barra de menú"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: showMenubar
                                objectName: "settings.appearance.showMenubar"
                                checked: root._loadValue("interface/show_menubar", true)
                                onClicked: root._saveValue("interface/show_menubar", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mostrar barra de menú"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
