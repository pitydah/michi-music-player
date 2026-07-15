import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
<<<<<<< Updated upstream
    objectName: "settingsPlaybackPage"
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var audioDevices: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de reproducción"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadDevices()
    }

    function _loadDevices() {
        if (!root.bridge) return
        var devs = root.bridge.getValue("audio/output_devices")
        root.audioDevices = devs || []
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
            objectName: "settings.playback.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de reproducción"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Reproducción"
                    subtitle: "Volumen, transiciones y normalización"
                }

                GlassCard {
                    id: outputCard
                    Layout.fillWidth: true
                    title: "Salida de audio"
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
                                    text: "Dispositivo de salida"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Selecciona el dispositivo de audio"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: outputDevice
                                objectName: "settings.playback.outputDevice"
                                model: root.audioDevices.length > 0 ? root.audioDevices : ["Predeterminado"]
                                currentIndex: {
                                    var dev = root._loadValue("audio/output_device_id", "auto")
                                    for (var i = 0; i < model.count; i++)
                                        if (String(model[i]) === dev || model[i] === dev) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/output_device_id", currentText)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Dispositivo de salida"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

<<<<<<< Updated upstream
=======
                        ComboBox {
                            id: outputDeviceCombo
                            objectName: "settings.playback.outputDevice"
                            model: ["Predeterminado", "HDMI", "USB DAC", "Bluetooth"]
                            currentIndex: 0
                            Accessible.name: "Dispositivo de salida de audio"
                            KeyNavigation.tab: audioProfileCombo
=======
    objectName: "settingsPlaybackPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property var audioDevices: []

    Accessible.role: Accessible.Pane
    Accessible.name: "Ajustes de reproducción"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadDevices()
    }

    function _loadDevices() {
        if (!root.bridge) return
        var devs = root.bridge.getValue("audio/output_devices")
        root.audioDevices = devs || []
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
            objectName: "settings.playback.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Ajustes de reproducción"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                bottomPadding: MichiTheme.spacing.xl

                PageHeader {
                    title: "Reproducción"
                    subtitle: "Volumen, transiciones y normalización"
                }

                GlassCard {
                    id: outputCard
                    Layout.fillWidth: true
                    title: "Salida de audio"
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
                                    text: "Dispositivo de salida"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Selecciona el dispositivo de audio"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: outputDevice
                                objectName: "settings.playback.outputDevice"
                                model: root.audioDevices.length > 0 ? root.audioDevices : ["Predeterminado"]
                                currentIndex: {
                                    var dev = root._loadValue("audio/output_device_id", "auto")
                                    for (var i = 0; i < model.count; i++)
                                        if (String(model[i]) === dev || model[i] === dev) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/output_device_id", currentText)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Dispositivo de salida"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

>>>>>>> Stashed changes
                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Perfil de audio"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Estándar, Hi-Fi, Bit-Perfect, DSD"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            ComboBox {
                                id: audioProfile
                                objectName: "settings.playback.audioProfile"
                                model: ["standard", "hifi_pcm", "bitperfect_pcm", "dsd_to_pcm", "pure_audio", "studio_monitor"]
                                currentIndex: {
                                    var p = root._loadValue("audio/profile", "standard")
                                    for (var i = 0; i < model.count; i++)
                                        if (model[i] === p) return i
                                    return 0
                                }
                                onActivated: root._saveValue("audio/profile", currentText)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Perfil de audio"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
                GlassCard {
                    id: volumeCard
                    Layout.fillWidth: true
                    title: "Volumen"
                    interactive: false
=======
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
                                    text: "Volumen predeterminado"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: defaultVolumeSlider.value + "%"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: defaultVolumeSlider
                                objectName: "settings.playback.defaultVolume"
                                implicitWidth: 200
                                from: 0
                                to: 100
                                value: root._loadValue("playback/default_volume", 70)
                                accessibleName: "Volumen predeterminado"
                                onMoved: {}
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("playback/default_volume", value)
                                }
                                Accessible.description: "Nivel de volumen al iniciar la aplicación"
                            }
                        }

<<<<<<< Updated upstream
=======
                        ComboBox {
                            id: audioProfileCombo
                            objectName: "settings.playback.audioProfile"
                            model: ["Estándar", "Hi-Fi", "Bit-perfect", "MPD"]
                            currentIndex: 0
                            Accessible.name: "Perfil de audio"
                            KeyNavigation.tab: volumeSlider
=======
                GlassCard {
                    id: volumeCard
                    Layout.fillWidth: true
                    title: "Volumen"
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
                                    text: "Volumen predeterminado"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: defaultVolumeSlider.value + "%"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: defaultVolumeSlider
                                objectName: "settings.playback.defaultVolume"
                                implicitWidth: 200
                                from: 0
                                to: 100
                                value: root._loadValue("playback/default_volume", 70)
                                accessibleName: "Volumen predeterminado"
                                onMoved: {}
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("playback/default_volume", value)
                                }
                                Accessible.description: "Nivel de volumen al iniciar la aplicación"
                            }
                        }

>>>>>>> Stashed changes
                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Recordar volumen"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: rememberVolume
                                objectName: "settings.playback.rememberVolume"
                                checked: root._loadValue("playback/remember_volume", true)
                                onClicked: root._saveValue("playback/remember_volume", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Recordar volumen"
                                Accessible.description: "Restaurar el último volumen usado"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
                GlassCard {
                    id: transitionsCard
                    Layout.fillWidth: true
                    title: "Transiciones"
                    interactive: false
=======
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
                                text: "Reproducción sin pausas (Gapless)"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: gaplessPlayback
                                objectName: "settings.playback.gapless"
                                checked: root._loadValue("playback/gapless", true)
                                onClicked: root._saveValue("playback/gapless", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Reproducción sin pausas"
                                Accessible.description: "Eliminar el silencio entre canciones"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

<<<<<<< Updated upstream
=======
                        Text {
                            text: Math.round(volumeSlider.value) + "%"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            implicitWidth: 40
=======
                GlassCard {
                    id: transitionsCard
                    Layout.fillWidth: true
                    title: "Transiciones"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md
                            Label {
                                text: "Reproducción sin pausas (Gapless)"
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                            Switch {
                                id: gaplessPlayback
                                objectName: "settings.playback.gapless"
                                checked: root._loadValue("playback/gapless", true)
                                onClicked: root._saveValue("playback/gapless", checked)
                                Accessible.role: Accessible.CheckBox
                                Accessible.name: "Reproducción sin pausas"
                                Accessible.description: "Eliminar el silencio entre canciones"
                                focusPolicy: Qt.StrongFocus
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

>>>>>>> Stashed changes
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.md

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: "Crossfade"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: crossfadeSlider.value + " s"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: crossfadeSlider
                                objectName: "settings.playback.crossfade"
                                implicitWidth: 200
                                from: 0
                                to: 10
                                value: root._loadValue("playback/crossfade", 0)
                                stepSize: 0.5
                                accessibleName: "Crossfade"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("playback/crossfade", value)
                                }
                                Accessible.description: "Duración del fundido entre canciones"
                            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
                GlassCard {
                    id: replaygainCard
                    Layout.fillWidth: true
                    title: "ReplayGain"
                    interactive: false
=======
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
                                    text: "Normalización de volumen"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Ajusta el volumen según metadatos ReplayGain"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

<<<<<<< Updated upstream
=======
                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Crossfade"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: crossfadeSwitch
                            objectName: "settings.playback.crossfade"
                            checked: false
                            Accessible.name: "Crossfade entre canciones"
                            KeyNavigation.tab: crossfadeDurationSlider
                        }

                        MichiSlider {
                            id: crossfadeDurationSlider
                            objectName: "settings.playback.crossfadeDuration"
                            Layout.preferredWidth: 120
                            from: 0; to: 12; value: 3
                            stepSize: 1
                            enabled: crossfadeSwitch.checked
                            accessibleName: "Duración de crossfade"
                            KeyNavigation.tab: replaygainCombo
                        }

                        Text {
                            text: crossfadeDurationSlider.value + " s"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.captionSize
                            implicitWidth: 36
=======
                GlassCard {
                    id: replaygainCard
                    Layout.fillWidth: true
                    title: "ReplayGain"
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
                                    text: "Normalización de volumen"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: "Ajusta el volumen según metadatos ReplayGain"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

>>>>>>> Stashed changes
                            ComboBox {
                                id: replaygainMode
                                objectName: "settings.playback.replaygainMode"
                                model: ListModel {
                                    ListElement { text: "Desactivado"; value: "off" }
                                    ListElement { text: "Pista (Track)"; value: "track" }
                                    ListElement { text: "Álbum (Album)"; value: "album" }
                                    ListElement { text: "Automático"; value: "auto" }
                                }
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: {
                                    var m = root._loadValue("playback/replaygain", "off")
                                    for (var i = 0; i < model.count; i++)
                                        if (model.get(i).value === m) return i
                                    return 0
                                }
                                onActivated: root._saveValue("playback/replaygain", currentValue)
                                Accessible.role: Accessible.ComboBox
                                Accessible.name: "Modo ReplayGain"
                                focusPolicy: Qt.StrongFocus
                            }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                        }
                    }
                }

<<<<<<< Updated upstream
                GlassCard {
                    id: bufferCard
                    Layout.fillWidth: true
                    title: "Buffer"
                    interactive: false
=======
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
                                    text: "Tamaño de buffer"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: bufferSizeSlider.value + " ms"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: bufferSizeSlider
                                objectName: "settings.playback.bufferSize"
                                implicitWidth: 200
                                from: 50
                                to: 1000
                                value: root._loadValue("audio/buffer_ms", 100)
                                stepSize: 50
                                accessibleName: "Tamaño de buffer"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("audio/buffer_ms", value)
                                }
                                Accessible.description: "Tamaño del buffer de audio en milisegundos"
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
<<<<<<< Updated upstream
=======
=======
                GlassCard {
                    id: bufferCard
                    Layout.fillWidth: true
                    title: "Buffer"
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
                                    text: "Tamaño de buffer"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                                Label {
                                    text: bufferSizeSlider.value + " ms"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            MichiSlider {
                                id: bufferSizeSlider
                                objectName: "settings.playback.bufferSize"
                                implicitWidth: 200
                                from: 50
                                to: 1000
                                value: root._loadValue("audio/buffer_ms", 100)
                                stepSize: 50
                                accessibleName: "Tamaño de buffer"
                                onPressedChanged: {
                                    if (!pressed) root._saveValue("audio/buffer_ms", value)
                                }
                                Accessible.description: "Tamaño del buffer de audio en milisegundos"
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
>>>>>>> Stashed changes

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
}
