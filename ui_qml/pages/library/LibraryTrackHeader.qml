import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Track Header"
    objectName: "libraryTrackHeader"
    focus: true
    id: root
    width: parent.width; height: 28

    property var bridge: null
    property string sortKey: "title"
    property bool sortAsc: true

    color: MichiTheme.colors.surfaceCard

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: MichiTheme.spacing.md
        anchors.rightMargin: MichiTheme.spacing.sm
        spacing: 0

        Item { width: 20; height: 1 }

        Item { width: 30; height: 1 }

        Repeater {
            model: [
                {label: "Título", key: "title", width: 0.28},
                {label: "Artista", key: "artist", width: 0.22},
                {label: "Álbum", key: "album", width: 0.22},
                {label: "Cal.", key: "", width: 40},
                {label: "Año", key: "year", width: 40, right: true},
                {label: "Dur.", key: "duration", width: 48, right: true},
            ]

            Rectangle {
                width: modelData.width.toString().indexOf(".") >= 0 ? parent.width * parseFloat(modelData.width) : parseInt(modelData.width)
                height: parent.height
                color: "transparent"

                Text {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    anchors.rightMargin: MichiTheme.spacing.xs
                    horizontalAlignment: modelData.right ? Text.AlignRight : Text.AlignLeft
                    text: modelData.label
                    color: root.bridge && root.bridge.activeSortKey === modelData.key ? MichiTheme.colors.accentBlue : MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    font.weight: root.bridge && root.bridge.activeSortKey === modelData.key ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightMedium
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (modelData.key && root.bridge && typeof root.bridge.sortBy !== "undefined")
                            root.bridge.sortBy(modelData.key)
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width; height: 1
        color: MichiTheme.colors.borderSubtle
    }
}
