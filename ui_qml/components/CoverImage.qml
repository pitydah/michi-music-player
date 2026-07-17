import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Cover Image"
    objectName: "coverImage"
    focus: true
    id: root

    property string coverKey: ""
    property int coverRadius: MichiTheme.radius.xs
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
            text: "MP"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.cardTitleSize
            font.weight: MichiTheme.typography.weightBold
            opacity: 0.7
            visible: bridgeLoader.status === Loader.Error || (bridgeLoader.status === Loader.Ready && !bridgeLoader.item.ready)
        }
    }
}
