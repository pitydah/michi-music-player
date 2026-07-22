import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Queue Item"
    objectName: "queueItem_control"
    focus: true
    id: root

    property var qb: null
    property var ps: null
    property var notif: null
    property int itemIndex: -1
    property string itemTitle: ""
    property string itemArtist: ""
    property string itemAlbum: ""
    property int itemDuration: 0
    property bool itemIsCurrent: false

    Rectangle {
        anchors.fill: parent
        color: root.itemIsCurrent ? MichiTheme.colors.accentSelection : MichiTheme.colors.surfaceCard
        radius: MichiTheme.radius.sm
        border.width: root.itemIsCurrent ? 1 : 0
        border.color: root.itemIsCurrent ? MichiTheme.colors.accentBlue : "transparent"

        RowLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.sm

            Text {
                text: (root.itemIndex + 1) + "."
                color: root.itemIsCurrent ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                width: 28
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    text: root.itemTitle || "—"
                    color: root.itemIsCurrent ? MichiTheme.colors.accentBlue : MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: root.itemIsCurrent ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: root.itemArtist ? root.itemArtist + (root.itemAlbum ? " · " + root.itemAlbum : "") : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    visible: text !== ""
                }
            }

            Text {
                text: formatDuration(root.itemDuration)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            MichiIconButton {
                iconSource: "../../icons/nowplaying_clean/warm_play_32.png"
                iconText: ""
                tooltipText: "Reproducir"
                btnSize: 24
                onClicked: {
                    if (root.qb) {
                        var result = root.qb.playFromIndex(root.itemIndex)
                        if (!result.ok && root.notif)
                            root.notif.showMessage(result.error || "Error", "error")
                    }
                }
            }

            MichiIconButton {
                iconSource: "../../icons/sidebar_clean/close_32.png"
                iconText: ""
                tooltipText: "Quitar de la cola"
                btnSize: 24
                onClicked: {
                    if (root.qb) {
                        root.qb.removeFromQueue(root.itemIndex)
                    }
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            acceptedButtons: Qt.NoButton
        }
    }

    function formatDuration(seconds) {
        var s = Math.max(0, Math.floor(seconds))
        var m = Math.floor(s / 60)
        s = s % 60
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
