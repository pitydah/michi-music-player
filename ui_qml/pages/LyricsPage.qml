import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var lb: typeof lyricsBridge !== "undefined" ? lyricsBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property bool showSynced: root.lb && root.lb.hasSyncedLyrics

    objectName: "lyrics.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Letra"
    Accessible.description: "Visualizador de letras de canciones"

    function routeEnter(route) {
        if (root.lb) root.lb.searchCurrentTrack()
    }

    Component.onCompleted: routeEnter("lyrics")

    Keys.onEscapePressed: {
        if (searchDialog.opened) searchDialog.close()
    }

    Column {
        id: mainColumn
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.md
        objectName: "lyrics.mainColumn"

        Row {
            id: headerRow
            width: parent.width; spacing: MichiTheme.spacing.sm
            objectName: "lyrics.headerRow"

            Text {
                id: titleText
                text: "Letra"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                objectName: "lyrics.title"
                Accessible.role: Accessible.Heading
                Accessible.name: "Letra"
            }
            Item { width: 1; height: 1; }
            StatusBadge {
                id: statusBadge
                text: root.lb ? root.lb.status : "idle"
                kind: root.lb && root.lb.status === "done" ? "success" :
                      root.lb && root.lb.status === "searching" ? "warning" :
                      root.lb && root.lb.status === "not_found" ? "disconnected" : "info"
                objectName: "lyrics.statusBadge"
            }
            Item { width: 1; height: 1 }
            MichiButton {
                id: searchOtherBtn
                text: "Buscar otra versión"
                visible: root.lb && root.lb.status === "done"
                variant: "ghost"
                objectName: "lyrics.searchOther"
                Accessible.name: "Buscar otra versión de letra"
                onClicked: searchDialog.open()
            }
        }

        Text {
            id: trackInfoText
            text: root.np ? (root.np.trackTitle || "") + " — " + (root.np.trackArtist || "") : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            visible: text !== ""
            objectName: "lyrics.trackInfo"
        }

        Item {
            id: contentArea
            width: parent.width
            height: parent.height - y - MichiTheme.spacing.xl
            objectName: "lyrics.contentArea"

            Text {
                id: loadingText
                text: "Buscando letra..."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.centerIn: parent
                visible: root.lb && root.lb.status === "searching"
                objectName: "lyrics.loadingState"
                Accessible.name: "Buscando letra"
            }

            Column {
                id: notFoundColumn
                anchors.centerIn: parent; spacing: MichiTheme.spacing.md
                visible: root.lb && root.lb.status === "not_found"
                objectName: "lyrics.notFoundState"

                Text {
                    text: "Letra no encontrada"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                    anchors.horizontalCenter: parent.horizontalCenter
                    Accessible.name: "Letra no encontrada"
                }
                Text {
                    text: "Puedes buscar manualmente"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                MichiButton {
                    id: searchManualBtn
                    text: "Buscar manualmente"
                    variant: "ghost"
                    objectName: "lyrics.searchManual"
                    Accessible.name: "Buscar letra manualmente"
                    onClicked: searchDialog.open()
                }
            }

            Text {
                id: errorText
                text: root.lb && root.lb.status === "error" ? "Error: " + root.lb.errorMessage : ""
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.centerIn: parent
                visible: text !== ""
                objectName: "lyrics.errorState"
                Accessible.name: text
            }

            SyncedLyricsView {
                id: syncedView
                anchors.fill: parent
                visible: root.showSynced && root.lb && root.lb.status === "done"
                lyricsBridge: root.lb
                nowplayingBridge: root.np
                currentPositionMs: root.np ? root.np.position : 0
            }

            Flickable {
                id: plainLyricsFlickable
                anchors.fill: parent
                contentHeight: plainText.height + MichiTheme.spacing.xl
                clip: true; boundsBehavior: Flickable.StopAtBounds
                visible: !root.showSynced && root.lb && root.lb.status === "done"
                objectName: "lyrics.plainView"

                Text {
                    id: plainText
                    text: root.lb ? root.lb.lyrics : ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.6
                    Accessible.name: root.lb ? root.lb.lyrics : ""
                }
            }
        }
    }

    LyricsSearchDialog {
        id: searchDialog
        lyricsBridge: root.lb
    }

    Text {
        id: attributionText
        anchors.bottom: parent.bottom; anchors.right: parent.right
        anchors.margins: MichiTheme.spacing.sm
        text: root.lb && root.lb.source ? "Fuente: " + root.lb.source : ""
        color: MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.captionSize
        visible: root.lb && root.lb.status === "done"
        objectName: "lyrics.attribution"
        Accessible.name: text
    }
}
