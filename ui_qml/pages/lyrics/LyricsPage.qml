import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root
    objectName: "lyricsPage"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Letra"

    property var lb: typeof lyricsBridge !== "undefined" ? lyricsBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property bool showSynced: root.lb && root.lb.hasSyncedLyrics
    property int _offsetMs: 0

    enum State { LOADING, READY, EMPTY, ERROR, UNAVAILABLE }
    property int pageState: root.lb ? LyricsPage.READY : LyricsPage.UNAVAILABLE

    function routeEnter(route) {
        if (root.lb && root.lb.status === "idle")
            root.lb.searchCurrentTrack()
    }

    Component.onCompleted: routeEnter("lyrics")

    StackLayout {
        anchors.fill: parent
        currentIndex: {
            if (!root.lb || root.pageState === LyricsPage.UNAVAILABLE) return 0
            if (root.lb.status === "searching") return 1
            if (root.lb.status === "not_found" || root.lb.status === "") return 2
            if (root.lb.status === "error") return 3
            return 4
        }

        UnavailableState {
            title: "Servicio de letras no disponible"
            message: "Conecta un reproductor para buscar letras."
        }

        LoadingState {
            title: "Buscando letra..."
        }

        EmptyState {
            title: "Letra no encontrada"
            subtitle: "Prueba con una búsqueda manual."
        }

        ErrorState {
            title: "Error al buscar letra"
            message: root.lb ? (root.lb.errorMessage || "") : ""
            showRetry: true
            onRetryRequested: { if (root.lb) root.lb.searchCurrentTrack() }
        }

        Flickable {
            anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Row {
                width: parent.width; spacing: MichiTheme.spacing.sm

                Text {
                    text: "Letra"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                StatusBadge {
                    text: root.lb ? root.lb.status : "idle"
                    kind: root.lb && root.lb.status === "done" ? "success" :
                          root.lb && root.lb.status === "searching" ? "warning" :
                          root.lb && root.lb.status === "error" ? "error" :
                          root.lb && root.lb.status === "not_found" ? "disconnected" : "info"
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                Text {
                    text: root.np ? (root.np.trackTitle || "") + " — " + (root.np.trackArtist || "") : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: text !== ""
                }
                Text {
                    text: root.lb && root.lb.source ? "Fuente: " + root.lb.source : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    visible: text !== ""
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.lb && root.lb.status === "done"

                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: "Buscar otra versión"
                    variant: "ghost"
                    onClicked: searchDialog.open()
                }
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true


                MichiButton {
                    text: root.showSynced ? "Ver texto plano" : "Ver sincronizada"
                    variant: "ghost"
                    visible: root.lb && root.lb.hasSyncedLyrics
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    onClicked: root.showSynced = !root.showSynced
                }

                MichiButton {
                    text: "Editar letra"
                    variant: "ghost"
                    onClicked: editDialog.open()
                }
            }

            Item {
                width: parent.width
                height: Math.max(300, parent.height - y - MichiTheme.spacing.xl)

                Text {
                    text: "Buscando letra..."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.centerIn: parent
                    visible: root.lb && root.lb.status === "searching"
                }

                Text {
                    text: "Letra no encontrada"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.centerIn: parent
                    visible: root.lb && root.lb.status === "not_found"
                }

                Text {
                    text: root.lb && root.lb.status === "error" ? "Error: " + (root.lb.errorMessage || "") : ""
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.centerIn: parent
                    visible: text !== ""
                }

                SyncedLyricsView {
                    id: syncedView
                    anchors.fill: parent
                    visible: root.showSynced && root.lb && root.lb.status === "done"
                    lyricsBridge: root.lb
                    nowplayingBridge: root.np
                    currentPositionMs: (root.np ? root.np.position : 0) + root._offsetMs
                }

                Flickable {
                    anchors.fill: parent
                    contentHeight: plainText.height + MichiTheme.spacing.xl
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    visible: !root.showSynced && root.lb && root.lb.status === "done"

                    Text {
                        id: plainText
                        text: root.lb ? root.lb.lyrics : ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.6
                    }
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.lb && root.lb.status === "done" && root.showSynced
                    Accessible.role: Accessible.Slider

                    activeFocusOnTab: true

                Text {
                    text: "Offset (ms):"
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                }
                MichiSlider {
                    width: 150
                    from: -5000; to: 5000; value: root._offsetMs; stepSize: 100
                    onMoved: root._offsetMs = value
                }
                Text {
                    text: root._offsetMs >= 0 ? "+" + root._offsetMs : "" + root._offsetMs
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Row {
                spacing: MichiTheme.spacing.sm
                visible: root.lb && root.lb.status === "not_found"
                MichiButton {
                    text: "Buscar manualmente"
                    variant: "primary"
                    onClicked: searchDialog.open()
                }
            }
        }
    }
    }

    LyricsSearchDialog {
        id: searchDialog
        lyricsBridge: root.lb
    }

    LyricsEditDialog {
        id: editDialog
        lyricsBridge: root.lb
    }
}
