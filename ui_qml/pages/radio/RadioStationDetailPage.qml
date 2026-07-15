import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
>>>>>>> Stashed changes
    property var stationData: null

    property bool _isPlaying: false
    property bool _buffering: false
    property string _state: "STOPPED"
    property string _metadata: ""
    property string _error: ""
    property int _bufferProgress: 0
    property bool _isFav: stationData ? stationData.favorite : false

    signal playRequested(string url, string name)
    signal stopRequested()
    signal toggleFavRequested(int stationId)
    signal editRequested(var stationData)
    signal deleteRequested(string url)
    signal retryRequested()

    implicitHeight: detailColumn.height + MichiTheme.spacing.xl * 2

<<<<<<< Updated upstream
=======
    Accessible.role: Accessible.Panel
    Accessible.name: stationData ? stationData.name + " - Detalle de emisora" : "Detalle de emisora"
    Accessible.description: "Estado: " + _playState
=======
    property var radioBridge: typeof radioBridge !== "undefined" ? radioBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var stationData: null

    property bool _isPlaying: false
    property bool _buffering: false
    property string _state: "STOPPED"
    property string _metadata: ""
    property string _error: ""
    property int _bufferProgress: 0
    property bool _isFav: stationData ? stationData.favorite : false

    signal playRequested(string url, string name)
    signal stopRequested()
    signal toggleFavRequested(int stationId)
    signal editRequested(var stationData)
    signal deleteRequested(string url)
    signal retryRequested()

    implicitHeight: detailColumn.height + MichiTheme.spacing.xl * 2

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    objectName: "radioStationDetailPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Detalle de emisora: " + (stationData ? stationData.name || "" : "")
    Accessible.description: "Estado: " + root._state

    function play() {
        if (root.stationData) {
            root._state = "CONNECTING"
            root._buffering = true
            root._error = ""
            root.playRequested(root.stationData.url, root.stationData.name)
        }
    }

    function stop() {
        root._state = "STOPPED"
        root._buffering = false
        root._isPlaying = false
        root._bufferProgress = 0
        root.stopRequested()
    }

    function retry() {
        root._error = ""
        root.retryRequested()
        root.play()
    }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    GlassCard {
        width: parent.width
        height: root.implicitHeight
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        title: ""
        subtitle: ""

        Column {
            id: detailColumn
            width: parent.width
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        objectName: "radioStationDetailPage.card"

        Column {
            anchors.fill: parent
=======
        title: ""
        subtitle: ""

        Column {
            id: detailColumn
            width: parent.width
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                spacing: MichiTheme.spacing.md
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                spacing: MichiTheme.spacing.sm
                objectName: "radioStationDetailPage.headerRow"
>>>>>>> Stashed changes

                Rectangle {
                    width: 64
                    height: 64
                    radius: MichiTheme.radiusMd
                    color: MichiTheme.colors.accentFaint

                    Text {
                        anchors.centerIn: parent
                        text: "\u25E2"
                        color: MichiTheme.colors.accent
                        font.pixelSize: 28
                    }

                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Icono de emisora de radio"
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: root.stationData ? root.stationData.name || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                        width: parent.parent.width - 80
                    }

                    Text {
                        text: root.stationData ? root.stationData.url || "" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
<<<<<<< Updated upstream
                        width: parent.parent.width - 80
=======
                        width: parent.width
=======
                spacing: MichiTheme.spacing.md

                Rectangle {
                    width: 64
                    height: 64
                    radius: MichiTheme.radiusMd
                    color: MichiTheme.colors.accentFaint

                    Text {
                        anchors.centerIn: parent
                        text: "\u25E2"
                        color: MichiTheme.colors.accent
                        font.pixelSize: 28
                    }

                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Icono de emisora de radio"
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: root.stationData ? root.stationData.name || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                        width: parent.parent.width - 80
                    }

                    Text {
                        text: root.stationData ? root.stationData.url || "" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.parent.width - 80
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    }
                }
            }

<<<<<<< Updated upstream
<<<<<<< Updated upstream
            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
            Text {
                text: stationData ? (stationData.genre || "") : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
                objectName: "radioStationDetailPage.genre"
            }

            Text {
                text: stationData ? (stationData.url || "") : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                elide: Text.ElideMiddle
                visible: text !== ""
                objectName: "radioStationDetailPage.url"
>>>>>>> Stashed changes
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.xl

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && (root.stationData.codec || "")

                    Text {
                        text: "Códec"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? root.stationData.codec || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && (root.stationData.country || "")

                    Text {
                        text: "País"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? root.stationData.country || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && root.stationData.tags && root.stationData.tags.length > 0

                    Text {
                        text: "Géneros"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? (root.stationData.tags || []).join(", ") : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
                visible: root._state !== "STOPPED"
            }

            Column {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                visible: root._state !== "STOPPED"

                Text {
                    text: {
                        switch (root._state) {
                            case "CONNECTING": return "Conectando..."
                            case "BUFFERING": return "Buffering..."
                            case "PLAYING": return "Reproduciendo"
                            case "RECONNECTING": return "Reconectando..."
                            case "FAILED": return "Error de conexión"
                            default: return ""
                        }
                    }
<<<<<<< Updated upstream
=======
                    objectName: "radioStationDetailPage.playButton"
                    Accessible.name: root._playState === "PLAYING" ? "Detener reproducción" : "Reproducir emisora"
=======
            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.xl

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && (root.stationData.codec || "")

                    Text {
                        text: "Códec"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? root.stationData.codec || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && (root.stationData.country || "")

                    Text {
                        text: "País"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? root.stationData.country || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }

                Column {
                    spacing: MichiTheme.spacing.xs
                    visible: root.stationData && root.stationData.tags && root.stationData.tags.length > 0

                    Text {
                        text: "Géneros"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }

                    Text {
                        text: root.stationData ? (root.stationData.tags || []).join(", ") : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
                visible: root._state !== "STOPPED"
            }

            Column {
                width: parent.width
                spacing: MichiTheme.spacing.xs
                visible: root._state !== "STOPPED"

                Text {
                    text: {
                        switch (root._state) {
                            case "CONNECTING": return "Conectando..."
                            case "BUFFERING": return "Buffering..."
                            case "PLAYING": return "Reproduciendo"
                            case "RECONNECTING": return "Reconectando..."
                            case "FAILED": return "Error de conexión"
                            default: return ""
                        }
                    }
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                    color: {
                        switch (root._state) {
                            case "PLAYING": return MichiTheme.colors.success
                            case "FAILED": return MichiTheme.colors.error
                            case "RECONNECTING": return MichiTheme.colors.warning
                            default: return MichiTheme.colors.textSecondary
                        }
                    }
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                }

                StatusBadge {
                    text: {
                        if (root._buffering) return "Buffering " + root._bufferProgress + "%"
                        if (root._state === "PLAYING") return "En vivo"
                        if (root._state === "FAILED") return "Error"
                        return ""
                    }
                    kind: {
                        if (root._state === "PLAYING") return "success"
                        if (root._state === "FAILED") return "error"
                        if (root._buffering) return "warning"
                        return "info"
                    }
                    visible: root._state !== "STOPPED"
                }

                Text {
                    text: root._metadata
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: root._metadata !== ""
                    elide: Text.ElideRight
                    width: parent.width
                }

                MichiProgressBar {
                    width: parent.width
                    indeterminate: root._buffering && root._bufferProgress === 0
                    value: root._bufferProgress / 100.0
                    visible: root._buffering
                }
            }

            Text {
                text: root._error
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root._error !== ""
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Rectangle {
                width: parent.width
                height: 1
                color: MichiTheme.colors.borderSubtle
            }

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                MichiButton {
                    text: root._isPlaying ? "\u25A0 Detener" : "\u25B6 Reproducir"
                    variant: root._isPlaying ? "ghost" : "primary"
                    objectName: "playStopBtn"
                    Accessible.name: root._isPlaying ? "Detener emisora" : "Reproducir emisora"
                    activeFocusOnTab: true
                    onClicked: root._isPlaying ? root.stop() : root.play()
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                }

                MichiButton {
                    text: root._isFav ? "\u2605" : "\u2606"
                    variant: "ghost"
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                    objectName: "toggleFavBtn"
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                    tooltipText: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                    onClicked: {
                        root._isFav = !root._isFav
                        root.toggleFavRequested()
                    }
                    objectName: "radioStationDetailPage.favButton"
>>>>>>> Stashed changes
                    Accessible.name: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stationData) {
                            root.toggleFavRequested(root.stationData.id || 0)
                            root._isFav = !root._isFav
                        }
                    }
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u270E Editar"
                    variant: "ghost"
                    objectName: "editStationBtn"
                    Accessible.name: "Editar emisora"
                    activeFocusOnTab: true
                    visible: true
                    onClicked: root.editRequested(root.stationData)
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u2716"
                    variant: "danger"
                    objectName: "deleteStationBtn"
                    Accessible.name: "Eliminar emisora"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stationData) root.deleteRequested(root.stationData.url)
                    }
                    Keys.onReturnPressed: onClicked()
                }

<<<<<<< Updated upstream
=======
            Item {
                width: parent.width
                height: 20
                visible: root._playState === "BUFFERING" || root._playState === "CONNECTING"

                Rectangle {
                    width: parent.width * 0.6
                    height: 6
                    radius: MichiTheme.radiusXs
                    color: MichiTheme.colors.controlTrack
                    anchors.centerIn: parent

                    Rectangle {
                        width: parent.width * (root._bufferPercent / 100)
                        height: parent.height
                        radius: MichiTheme.radiusXs
                        color: MichiTheme.colors.accent
                    }
                }
            }

            Text {
                text: root._metadata
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
                visible: text !== ""
                objectName: "radioStationDetailPage.metadata"
            }

            Text {
                text: root._errorMessage
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                wrapMode: Text.WordWrap
                visible: root._playState === "FAILED" && root._errorMessage !== ""
                objectName: "radioStationDetailPage.errorText"
                Accessible.role: Accessible.Alert
                Accessible.name: "Error: " + root._errorMessage
            }

            Loader {
                width: parent.width
                height: active ? childrenRect.height : 0
                active: root._playState === "FAILED"

                sourceComponent: Row {
                    spacing: MichiTheme.spacing.md
                    anchors.horizontalCenter: parent.horizontalCenter

                    MichiButton {
                        text: "Reintentar"
                        variant: "primary"
                        onClicked: root.retryRequested()
                        objectName: "radioStationDetailPage.retryButton"
                        Accessible.name: "Reintentar reproducción"
                    }

                    MichiButton {
                        text: "Cerrar"
                        variant: "ghost"
                        onClicked: root.backRequested()
                        objectName: "radioStationDetailPage.dismissErrorButton"
                    }
=======
                    objectName: "toggleFavBtn"
                    Accessible.name: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stationData) {
                            root.toggleFavRequested(root.stationData.id || 0)
                            root._isFav = !root._isFav
                        }
                    }
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u270E Editar"
                    variant: "ghost"
                    objectName: "editStationBtn"
                    Accessible.name: "Editar emisora"
                    activeFocusOnTab: true
                    visible: true
                    onClicked: root.editRequested(root.stationData)
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u2716"
                    variant: "danger"
                    objectName: "deleteStationBtn"
                    Accessible.name: "Eliminar emisora"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stationData) root.deleteRequested(root.stationData.url)
                    }
                    Keys.onReturnPressed: onClicked()
                }

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                MichiButton {
                    text: "Reintentar"
                    variant: "ghost"
                    objectName: "retryStationBtn"
                    Accessible.name: "Reintentar conexión"
                    visible: root._state === "FAILED"
                    activeFocusOnTab: true
                    onClicked: root.retry()
                    Keys.onReturnPressed: root.retry()
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
}
