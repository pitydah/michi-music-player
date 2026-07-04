import QtQuick
import "../theme"

Item {
    id: root

    property string coverKey: ""
    property int coverRadius: MichiTheme.radiusXs
    property bool showPlaceholder: true

    Rectangle {
        anchors.fill: parent
        radius: coverRadius
        color: MichiTheme.colors.borderInner
        clip: true

        Loader {
            id: bridgeLoader
            anchors.fill: parent
            asynchronous: true
            source: "CoverBridgeProxy.qml"

            onLoaded: {
                bridgeLoader.item.coverKey = root.coverKey
            }
        }

        Column {
            anchors.centerIn: parent; spacing: 0
            visible: bridgeLoader.status === Loader.Error || (bridgeLoader.status === Loader.Ready && !bridgeLoader.item.ready)

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "MP"
                color: MichiTheme.colors.textMuted
                font.pixelSize: 16
                font.weight: MichiTheme.typography.weightBold
                opacity: 0.6
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "*"
                color: MichiTheme.colors.textMuted
                font.pixelSize: 10
                opacity: 0.4
            }
        }
    }
}
