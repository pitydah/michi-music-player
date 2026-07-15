import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var rd: typeof radioBridge !== "undefined" ? radioBridge : null
    property var stationData: null
    property string _playState: "STOPPED"
    property string _metadata: ""
    property int _bufferPercent: 0
    property int _reconnectAttempts: 0
    property bool _isFav: stationData ? stationData.favorite : false
    property string _errorMessage: ""

    signal playRequested()
    signal stopRequested()
    signal toggleFavRequested()
    signal retryRequested()
    signal backRequested()

    objectName: "radioStationDetailPage"
    implicitHeight: 280

    Accessible.role: Accessible.Panel
    Accessible.name: stationData ? stationData.name + " - Detalle de emisora" : "Detalle de emisora"
    Accessible.description: "Estado: " + _playState

    GlassCard {
        width: parent.width
        height: root.implicitHeight
        objectName: "radioStationDetailPage.card"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm
                objectName: "radioStationDetailPage.headerRow"

                MichiButton {
                    text: "\u2190"
                    variant: "ghost"
                    implicitWidth: 32
                    implicitHeight: 32
                    tooltipText: "Volver"
                    onClicked: root.backRequested()
                    objectName: "radioStationDetailPage.backButton"
                    Accessible.name: "Volver a lista de emisoras"
                }

                Column {
                    width: parent.width - 80
                    spacing: 2

                    Text {
                        text: stationData ? stationData.name || "" : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        elide: Text.ElideRight
                        width: parent.width
                        Accessible.role: Accessible.Heading
                        Accessible.name: text
                    }

                    Text {
                        text: stationData
                            ? [stationData.codec, stationData.country, stationData.language].filter(function(x) { return x && x !== "" }).join(" · ")
                            : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
            }

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
            }

            Row {
                spacing: MichiTheme.spacing.md
                anchors.horizontalCenter: parent.horizontalCenter

                MichiButton {
                    text: root._playState === "PLAYING" ? "\u23F9 Detener" : "\u25B6 Reproducir"
                    variant: root._playState === "PLAYING" ? "danger" : "primary"
                    enabled: root._playState !== "CONNECTING" && root._playState !== "BUFFERING" && root._playState !== "RECONNECTING"
                    onClicked: {
                        if (root._playState === "PLAYING") {
                            root.stopRequested()
                        } else {
                            root.playRequested()
                        }
                    }
                    objectName: "radioStationDetailPage.playButton"
                    Accessible.name: root._playState === "PLAYING" ? "Detener reproducción" : "Reproducir emisora"
                }

                MichiButton {
                    text: root._isFav ? "\u2605" : "\u2606"
                    variant: "ghost"
                    tooltipText: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                    onClicked: {
                        root._isFav = !root._isFav
                        root.toggleFavRequested()
                    }
                    objectName: "radioStationDetailPage.favButton"
                    Accessible.name: root._isFav ? "Quitar de favoritos" : "Añadir a favoritos"
                }
            }

            StatusBadge {
                id: playStateBadge
                text: {
                    switch (root._playState) {
                        case "CONNECTING": return "Conectando..."
                        case "BUFFERING": return "Buffering..."
                        case "PLAYING": return "Reproduciendo"
                        case "RECONNECTING": return "Reconectando..."
                        case "STOPPED": return "Detenido"
                        case "FAILED": return "Error"
                        default: return root._playState
                    }
                }
                kind: {
                    switch (root._playState) {
                        case "PLAYING": return "success"
                        case "CONNECTING": case "BUFFERING": case "RECONNECTING": return "warning"
                        case "FAILED": return "danger"
                        default: return "info"
                    }
                }
                anchors.horizontalCenter: parent.horizontalCenter
                visible: root._playState !== "STOPPED"
                objectName: "radioStationDetailPage.stateBadge"
            }

            Item {
                width: parent.width
                height: 20
                visible: root._playState === "BUFFERING" || root._playState === "CONNECTING"

                Rectangle {
                    width: parent.width * 0.6
                    height: 6
                    radius: 3
                    color: MichiTheme.colors.controlTrack
                    anchors.centerIn: parent

                    Rectangle {
                        width: parent.width * (root._bufferPercent / 100)
                        height: parent.height
                        radius: 3
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
                }
            }
        }
    }
}
