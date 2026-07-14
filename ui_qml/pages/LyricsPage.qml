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

    function routeEnter(route) {
        if (root.lb) root.lb.searchCurrentTrack()
    }

    Component.onCompleted: routeEnter("lyrics")

    Column {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        spacing: MichiTheme.spacing.md

        // Header
        Row {
            width: parent.width; spacing: MichiTheme.spacing.sm
            Text {
                text: "Letra"; color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }
            Item { width: 1; height: 1; }
            StatusBadge {
                text: root.lb ? root.lb.status : "idle"
                kind: root.lb && root.lb.status === "done" ? "success" :
                      root.lb && root.lb.status === "searching" ? "warning" :
                      root.lb && root.lb.status === "not_found" ? "disconnected" : "info"
            }
            Item { width: 1; height: 1 }
            Button {
                text: "Buscar otra versión"
                visible: root.lb && root.lb.status === "done"
                flat: true
                onClicked: searchDialog.open()
            }
        }

        // Track info
        Text {
            text: root.np ? (root.np.trackTitle || "") + " — " + (root.np.trackArtist || "") : ""
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            visible: text !== ""
        }

        // Content area
        Item {
            width: parent.width
            height: parent.height - y - MichiTheme.spacing.xl

            // Loading
            Text {
                text: "Buscando letra..."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.centerIn: parent
                visible: root.lb && root.lb.status === "searching"
            }

            // Not found
            Column {
                anchors.centerIn: parent; spacing: MichiTheme.spacing.md
                visible: root.lb && root.lb.status === "not_found"
                Text {
                    text: "Letra no encontrada"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Puedes buscar manualmente"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Button {
                    text: "Buscar manualmente"
                    anchors.horizontalCenter: parent.horizontalCenter
                    flat: true
                    onClicked: searchDialog.open()
                }
            }

            // Error
            Text {
                text: root.lb && root.lb.status === "error" ? "Error: " + root.lb.errorMessage : ""
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                anchors.centerIn: parent
                visible: text !== ""
            }

            // Synced lyrics view
            SyncedLyricsView {
                id: syncedView
                anchors.fill: parent
                visible: root.showSynced && root.lb && root.lb.status === "done"
                lyricsBridge: root.lb
                nowplayingBridge: root.np
                currentPositionMs: root.np ? root.np.position : 0
            }

            // Plain lyrics
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
    }

    // Search dialog
    LyricsSearchDialog {
        id: searchDialog
        lyricsBridge: root.lb
    }

    // Attribution
    Text {
        anchors.bottom: parent.bottom; anchors.right: parent.right
        anchors.margins: MichiTheme.spacing.sm
        text: root.lb && root.lb.source ? "Fuente: " + root.lb.source : ""
        color: MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.captionSize
        visible: root.lb && root.lb.status === "done"
    }
}
