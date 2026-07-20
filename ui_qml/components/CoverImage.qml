import QtQuick
import "../theme"

Item {
    id: root
    objectName: "coverImage"

    Accessible.role: Accessible.Graphic
    Accessible.name: qsTr("Carátula del álbum")

    property string coverKey: ""
    property int coverRadius: MichiTheme.radius.xs
    property bool showPlaceholder: true
    property string coverUrl: ""
    readonly property bool ready: coverArtwork.status === Image.Ready

    function refreshCover() {
        if (!root.coverKey || typeof coverProviderBridge === "undefined" || !coverProviderBridge) {
            root.coverUrl = ""
            return
        }
        root.coverUrl = coverProviderBridge.requestCover(
            root.coverKey,
            Math.max(64, Math.ceil(Math.max(root.width, root.height)))
        ) || ""
    }

    onCoverKeyChanged: refreshCover()
    Component.onCompleted: refreshCover()

    Rectangle {
        anchors.fill: parent
        radius: root.coverRadius
        color: MichiTheme.colors.borderInner
        clip: true

        Image {
            id: coverArtwork
            anchors.fill: parent
            source: root.coverUrl
            asynchronous: true
            cache: true
            fillMode: Image.PreserveAspectCrop
            sourceSize.width: Math.max(64, Math.ceil(width))
            sourceSize.height: Math.max(64, Math.ceil(height))
            visible: status === Image.Ready
        }

        Rectangle {
            anchors.fill: parent
            visible: root.showPlaceholder && !root.ready
            color: MichiTheme.colors.surfaceSubtle

            Text {
                anchors.centerIn: parent
                text: typeof coverProviderBridge !== "undefined" && coverProviderBridge
                      ? coverProviderBridge.getFallbackGlyph(root.coverKey)
                      : qsTr("MM")
                color: MichiTheme.colors.textMuted
                font.pixelSize: Math.max(14, Math.min(width, height) * 0.18)
                font.weight: MichiTheme.typography.weightBold
                opacity: 0.72
            }
        }
    }

    Connections {
        target: typeof coverProviderBridge !== "undefined" ? coverProviderBridge : null
        function onCoverReady(key, url) {
            if (key === root.coverKey)
                root.coverUrl = url || ""
        }
    }
}
