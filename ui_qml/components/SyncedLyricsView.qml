import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Synced Lyrics View"
    objectName: "syncedLyricsView"
    focus: true
    id: root

    property var lyricsBridge: null
    property var nowplayingBridge: null
    property real currentPositionMs: 0
    property bool autoScroll: true
    property real lineHeight: MichiTheme.typography.bodySize * 1.6

    signal toggledAutoScroll(bool enabled)

    function _activeLine() {
        if (!root.lyricsBridge || !root.lyricsBridge.syncedLyrics) return -1
        var lines = root.lyricsBridge.syncedLyrics
        var secs = root.currentPositionMs / 1000.0
        for (var i = 0; i < lines.length; i++) {
            if (lines[i].time > secs) return Math.max(0, i - 1)
        }
        return lines.length - 1
    }

    clip: true

    ListView {
        Accessible.role: Accessible.List

        Accessible.name: "ListView"

        activeFocusOnTab: true

        focusPolicy: Qt.StrongFocus
        id: listView
        anchors.fill: parent
        model: root.lyricsBridge ? root.lyricsBridge.syncedLyrics : []
        delegate: Item {
            width: listView.width
            height: root.lineHeight + MichiTheme.spacing.md
            property bool isActive: index === root._activeLine()

            Text {
                text: modelData ? modelData.text : ""
                color: parent.isActive ? MichiTheme.colors.accent : MichiTheme.colors.textSecondary
                font.pixelSize: parent.isActive ? MichiTheme.typography.bodySize * 1.15 : MichiTheme.typography.bodySize
                font.weight: parent.isActive ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                width: parent.width
                wrapMode: Text.WordWrap
                lineHeight: 1.4
                Behavior on color { ColorAnimation { duration: 150 } }
                Behavior on font.pixelSize { NumberAnimation { duration: 150 } }
            }
        }

        Timer {
            interval: 250
            running: root.autoScroll && root.lyricsBridge && root.lyricsBridge.hasSyncedLyrics
            repeat: true
            onTriggered: {
                var active = root._activeLine()
                if (active >= 0) {
                    listView.positionViewAtIndex(active, ListView.Contain)
                }
            }
        }

        onContentYChanged: {
            if (root.autoScroll) {
                var active = root._activeLine()
                if (active >= 0) {
                    var expectedY = active * (root.lineHeight + MichiTheme.spacing.md)
                    if (Math.abs(contentY - expectedY) > root.lineHeight) {
                        root.autoScroll = false
                    }
                }
            }
        }

        Connections {
            target: root
            function onCurrentPositionMsChanged() {
                if (root.autoScroll && root.lyricsBridge && root.lyricsBridge.hasSyncedLyrics) {
                    var active = root._activeLine()
                    if (active >= 0) {
                        listView.positionViewAtIndex(active, ListView.Contain)
                    }
                }
            }
        }
    }

    GlassMaterial {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: MichiTheme.spacing.xs
        width: 120; height: 32; radius: MichiTheme.radius.sm; variant: "status"
        visible: root.lyricsBridge && root.lyricsBridge.hasSyncedLyrics

        Row {
            anchors.centerIn: parent; spacing: MichiTheme.spacing.xs
            Text {
                text: root.autoScroll ? "\u25C0\u25B6" : qsTr("\u25B6\u25C0")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
                Accessible.role: Accessible.Icon
                Accessible.name: root.autoScroll ? "Desplazamiento automático activado" : "Desplazamiento manual activado"
                Accessible.description: "Haz clic para cambiar modo de desplazamiento"
            }
            Text {
                text: root.autoScroll ? "Auto" : qsTr("Manual")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.captionSize
            }
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    root.autoScroll = !root.autoScroll
                    root.toggledAutoScroll(root.autoScroll)
                }
            }
        }
    }
}
