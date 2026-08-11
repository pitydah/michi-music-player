import QtQuick
import QtQuick.Layouts
import "../theme"
import "../ui"

MichiPanel {
    id: root

    property alias fileName: trackLabel.text
    property alias position: seekSlider.value
    property alias duration: seekSlider.to
    property alias statusText: statusLabel.text
    property alias statusColor: statusLabel.color
    property bool seekEnabled: true

    signal seekRequested(int seconds)

    implicitHeight: 130

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.space8

        Text {
            id: trackLabel
            Layout.alignment: Qt.AlignHCenter
            text: "No track"
            font.pixelSize: MichiTheme.fontSizeBodyLarge
            color: MichiTheme.textSecondary
            elide: Text.ElideMiddle
            Layout.maximumWidth: 340
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            spacing: MichiTheme.space4

            Text {
                text: formatTime(seekSlider.value)
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                Layout.preferredWidth: 32
            }

            MichiSlider {
                id: seekSlider
                Layout.fillWidth: true
                from: 0; to: 1
                enabled: root.seekEnabled
                onMoved: root.seekRequested(value)
            }

            Text {
                text: formatTime(seekSlider.to)
                font.pixelSize: MichiTheme.fontSizeCaption
                color: MichiTheme.textSecondary
                Layout.preferredWidth: 32
            }
        }

        Text {
            id: statusLabel
            Layout.alignment: Qt.AlignHCenter
            font.pixelSize: MichiTheme.fontSizeCaption
        }
    }

    function formatTime(seconds) {
        if (seconds <= 0) return "0:00"
        var m = Math.floor(seconds / 60)
        var s = Math.floor(seconds % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
