import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Radio Station Detail"
    objectName: "radioStationDetailPage"
    focus: true
    id: root

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

    GlassCard {
        width: parent.width
        height: root.implicitHeight
        title: ""
        subtitle: ""

        Column {
            id: detailColumn
            width: parent.width
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
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
                    }
                }
            }

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
                    Accessible.role: Accessible.ProgressBar

                    activeFocusOnTab: true

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
                    Accessible.role: Accessible.Button


                MichiButton {
                    text: root._isPlaying ? "\u25A0 Detener" : "\u25B6 Reproducir"
                    variant: root._isPlaying ? "ghost" : "primary"
                    activeFocusOnTab: true
                    onClicked: root._isPlaying ? root.stop() : root.play()
                    Keys.onReturnPressed: onClicked()
                    Keys.onSpacePressed: onClicked()
                    Accessible.role: Accessible.Button

                }

                MichiButton {
                    text: root._isFav ? "\u2605" : "\u2606"
                    variant: "ghost"
                    activeFocusOnTab: true
                    onClicked: {
                        if (root.stationData) {
                            root.toggleFavRequested(root.stationData.id || 0)
                            root._isFav = !root._isFav
                        }
                    }
                    Accessible.role: Accessible.Button

                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u270E Editar"
                    variant: "ghost"
                    activeFocusOnTab: true
                    visible: true
                    Accessible.role: Accessible.Button

                    onClicked: root.editRequested(root.stationData)
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "\u2716"
                    variant: "danger"
                    activeFocusOnTab: true
                    onClicked: {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                        if (root.stationData) root.deleteRequested(root.stationData.url)
                    }
                    Keys.onReturnPressed: onClicked()
                }

                MichiButton {
                    text: "Reintentar"
                    variant: "ghost"
                    visible: root._state === "FAILED"
                    activeFocusOnTab: true
                    onClicked: root.retry()
                    Keys.onReturnPressed: root.retry()
                }
            }
        }
    }
}
