import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    objectName: "settingsAccessibilityPage"
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de accesibilidad"

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
            objectName: "settings.accessibility.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de accesibilidad"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Accesibilidad"
                    subtitle: "Audio, visión y preferencias de interacción"
                }

                GlassCard {
                    id: audioCard
                    Layout.fillWidth: true
                    title: "Audio"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mono"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: monoMode
                                objectName: "settings.accessibility.mono"
                                checked: root._loadValue("accessibility/mono", false)
                                onClicked: root._saveValue("accessibility/mono", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mono"
                                Accessible.description: "Mezclar canales estéreo a mono"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

<<<<<<< Updated upstream
=======
                        Switch {
                            id: reduceMotionSwitchAcc
                            objectName: "settings.accessibility.reduceMotion"
                            checked: root.bridge ? root.bridge.reduceMotion : false
                            Accessible.name: "Reducir movimiento"
                            Accessible.description: "Reducir animaciones y transiciones"
                            KeyNavigation.tab: announceTrackToggle
                            onClicked: {
                                if (root.bridge) root.bridge.reduceMotion = checked
=======
    objectName: "settingsAccessibilityPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de accesibilidad"

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
            objectName: "settings.accessibility.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de accesibilidad"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Accesibilidad"
                    subtitle: "Audio, visión y preferencias de interacción"
                }

                GlassCard {
                    id: audioCard
                    Layout.fillWidth: true
                    title: "Audio"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mono"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: monoMode
                                objectName: "settings.accessibility.mono"
                                checked: root._loadValue("accessibility/mono", false)
                                onClicked: root._saveValue("accessibility/mono", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mono"
                                Accessible.description: "Mezclar canales estéreo a mono"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Balance"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: balanceSlider.value.toFixed(1)
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: balanceSlider
                                objectName: "settings.accessibility.balance"
                                implicitWidth: 200
                                from: -1.0
                                to: 1.0
                                value: root._loadValue("accessibility/balance", 0.0)
                                stepSize: 0.1
                                accessibleName: "Balance"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("accessibility/balance", value)
                                }
                                Accessible.description: "Balance entre canal izquierdo y derecho"
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
                }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
                GlassCard {
                    id: visionCard
                    Layout.fillWidth: true
                    title: "Visión"
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
                            }

                            MichiSlider {
                                id: fontScaleSlider
                                objectName: "settings.accessibility.fontScale"
                                implicitWidth: 200
                                from: 75
                                to: 150
                                value: root._loadValue("accessibility/font_scale", 100)
                                stepSize: 5
                                accessibleName: "Escala de fuente"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("accessibility/font_scale", value)
                                }
                                Accessible.description: "Ajustar tamaño de fuente"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Alto contraste"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: highContrast
                                objectName: "settings.accessibility.highContrast"
                                checked: root._loadValue("accessibility/high_contrast", false)
                                onClicked: root._saveValue("accessibility/high_contrast", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Alto contraste"
                                Accessible.description: "Aumentar el contraste visual de la interfaz"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

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
                                objectName: "settings.accessibility.reducedMotion"
                                checked: root._loadValue("accessibility/reduced_motion", false)
                                onClicked: root._saveValue("accessibility/reduced_motion", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Movimiento reducido"
                                Accessible.description: "Minimizar animaciones y movimientos"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: screenReaderCard
                    Layout.fillWidth: true
                    title: "Lector de pantalla"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Soporte para lectores de pantalla"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: screenReader
                                objectName: "settings.accessibility.screenReader"
                                checked: root._loadValue("accessibility/screen_reader", false)
                                onClicked: root._saveValue("accessibility/screen_reader", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Soporte para lectores de pantalla"
                                Accessible.description: "Optimizar la interfaz para software de lectura de pantalla"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: announcementsCard
                    Layout.fillWidth: true
                    title: "Anuncios"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de notificaciones"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: notificationAnnouncements
                                objectName: "settings.accessibility.notificationAnnouncements"
                                checked: root._loadValue("accessibility/announce_notifications", true)
                                onClicked: root._saveValue("accessibility/announce_notifications", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de notificaciones"
                                Accessible.description: "Anunciar notificaciones mediante el lector de pantalla"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de errores"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: errorAnnouncements
                                objectName: "settings.accessibility.errorAnnouncements"
                                checked: root._loadValue("accessibility/announce_errors", true)
                                onClicked: root._saveValue("accessibility/announce_errors", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de errores"
                                Accessible.description: "Anunciar mensajes de error"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de estado de reproducción"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: playbackAnnouncements
                                objectName: "settings.accessibility.playbackAnnouncements"
                                checked: root._loadValue("accessibility/announce_playback", true)
                                onClicked: root._saveValue("accessibility/announce_playback", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de estado de reproducción"
                                Accessible.description: "Anunciar cambios de canción y estado"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: keyboardCard
                    Layout.fillWidth: true
                    title: "Atajos de teclado"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mostrar indicadores de atajos"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: showShortcuts
                                objectName: "settings.accessibility.showShortcuts"
                                checked: root._loadValue("accessibility/show_shortcuts", true)
                                onClicked: root._saveValue("accessibility/show_shortcuts", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mostrar indicadores de atajos de teclado"
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
                    id: visionCard
                    Layout.fillWidth: true
                    title: "Visión"
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
                            }

                            MichiSlider {
                                id: fontScaleSlider
                                objectName: "settings.accessibility.fontScale"
                                implicitWidth: 200
                                from: 75
                                to: 150
                                value: root._loadValue("accessibility/font_scale", 100)
                                stepSize: 5
                                accessibleName: "Escala de fuente"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("accessibility/font_scale", value)
                                }
                                Accessible.description: "Ajustar tamaño de fuente"
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Alto contraste"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: highContrast
                                objectName: "settings.accessibility.highContrast"
                                checked: root._loadValue("accessibility/high_contrast", false)
                                onClicked: root._saveValue("accessibility/high_contrast", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Alto contraste"
                                Accessible.description: "Aumentar el contraste visual de la interfaz"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

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
                                objectName: "settings.accessibility.reducedMotion"
                                checked: root._loadValue("accessibility/reduced_motion", false)
                                onClicked: root._saveValue("accessibility/reduced_motion", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Movimiento reducido"
                                Accessible.description: "Minimizar animaciones y movimientos"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: screenReaderCard
                    Layout.fillWidth: true
                    title: "Lector de pantalla"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Soporte para lectores de pantalla"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: screenReader
                                objectName: "settings.accessibility.screenReader"
                                checked: root._loadValue("accessibility/screen_reader", false)
                                onClicked: root._saveValue("accessibility/screen_reader", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Soporte para lectores de pantalla"
                                Accessible.description: "Optimizar la interfaz para software de lectura de pantalla"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: announcementsCard
                    Layout.fillWidth: true
                    title: "Anuncios"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de notificaciones"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: notificationAnnouncements
                                objectName: "settings.accessibility.notificationAnnouncements"
                                checked: root._loadValue("accessibility/announce_notifications", true)
                                onClicked: root._saveValue("accessibility/announce_notifications", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de notificaciones"
                                Accessible.description: "Anunciar notificaciones mediante el lector de pantalla"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de errores"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: errorAnnouncements
                                objectName: "settings.accessibility.errorAnnouncements"
                                checked: root._loadValue("accessibility/announce_errors", true)
                                onClicked: root._saveValue("accessibility/announce_errors", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de errores"
                                Accessible.description: "Anunciar mensajes de error"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Anuncios de estado de reproducción"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: playbackAnnouncements
                                objectName: "settings.accessibility.playbackAnnouncements"
                                checked: root._loadValue("accessibility/announce_playback", true)
                                onClicked: root._saveValue("accessibility/announce_playback", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Anuncios de estado de reproducción"
                                Accessible.description: "Anunciar cambios de canción y estado"
                                focusPolicy: Qt.StrongFocus
                            }
                        }
                    }
                }

                GlassCard {
                    id: keyboardCard
                    Layout.fillWidth: true
                    title: "Atajos de teclado"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Mostrar indicadores de atajos"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: showShortcuts
                                objectName: "settings.accessibility.showShortcuts"
                                checked: root._loadValue("accessibility/show_shortcuts", true)
                                onClicked: root._saveValue("accessibility/show_shortcuts", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Mostrar indicadores de atajos de teclado"
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
