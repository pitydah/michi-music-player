import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

Item {
    id: root

    property var lb: typeof lyricsBridge !== "undefined" ? lyricsBridge : null
    property var np: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null

    function routeEnter(route) {
        if (root.lb && root.np) {
            root.lb.search(root.np.trackTitle, root.np.trackArtist)
        }
    }

    Component.onCompleted: routeEnter("lyrics")

    Flickable {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column; width: parent.width; spacing: MichiTheme.spacing.lg

            Text { text: "Letra"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize; font.weight: MichiTheme.typography.weightSemiBold }

            StatusBadge {
                text: root.lb ? root.lb.status : "idle"
                kind: root.lb && root.lb.status === "done" ? "success" :
                      root.lb && root.lb.status === "searching" ? "warning" :
                      root.lb && root.lb.status === "not_found" ? "disconnected" : "info"
            }

            Text {
                text: root.lb ? root.lb.lyrics : ""
                color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.6
                visible: text !== ""
            }

            Text {
                text: root.lb && root.lb.status === "not_found" ? "Letra no encontrada para esta canción." : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            Text {
                text: root.lb && root.lb.status === "error" ? "Error: " + root.lb.errorMessage : ""
                color: MichiTheme.colors.error; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            GlassMaterial { width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column { anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Experimental — LRCLIB"; kind: "experimental" }
                }
            }
        }
    }
}
