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

        Text {
            anchors.centerIn: parent
            text: root.coverKey ? root.coverKey.charAt(0).toUpperCase() : "?"
            color: MichiTheme.colors.textMuted
            font.pixelSize: 14
            font.weight: MichiTheme.typography.weightBold
            visible: bridgeLoader.status === Loader.Error || (bridgeLoader.status === Loader.Ready && !bridgeLoader.item.ready)
        }
    }
}
