import QtQuick
import "../theme"

Item {
    id: root
    objectName: "coverImage"

    Accessible.role: Accessible.Graphic
    Accessible.name: root.accessibleLabel

    property string coverKey: ""
    property string fallbackTitle: ""
    property int coverRadius: MichiTheme.radius.xs
    property bool showPlaceholder: true
    property string coverUrl: ""
    property string artworkState: "idle"
    property bool reducedMotion: MichiTheme.reducedMotion || MichiTheme.motion.reducedMotion
    readonly property int fadeDuration: root.reducedMotion ? 0 : MichiTheme.motion.durationNormal
    readonly property string placeholderText: root.initialsForTitle(root.fallbackTitle)
    readonly property string accessibleLabel: root.fallbackTitle || qsTr("Carátula del álbum")
    readonly property bool ready: root.artworkState === "ready"

    function initialsForTitle(title) {
        const words = String(title || "").trim().split(/\s+/).filter(Boolean)
        if (words.length === 0)
            return ""
        if (words.length === 1)
            return words[0].slice(0, 2).toUpperCase()
        return (words[0][0] + words[1][0]).toUpperCase()
    }

    function refreshCover() {
        if (!root.coverKey || typeof coverProviderBridge === "undefined" || !coverProviderBridge) {
            root.coverUrl = ""
            root.artworkState = root.coverKey ? "missing" : "idle"
            return
        }
        const requestedKey = root.coverKey
        root.artworkState = "loading"
        const resolvedUrl = coverProviderBridge.requestCover(
            requestedKey,
            Math.max(64, Math.ceil(Math.max(root.width, root.height)))
        ) || ""
        if (requestedKey !== root.coverKey)
            return
        root.coverUrl = resolvedUrl
        root.artworkState = resolvedUrl ? "loading" : "missing"
    }

    onCoverKeyChanged: {
        root.coverUrl = ""
        root.artworkState = root.coverKey ? "loading" : "idle"
        root.refreshCover()
    }
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
            opacity: status === Image.Ready ? 1 : 0

            onStatusChanged: {
                if (status === Image.Ready)
                    root.artworkState = "ready"
                else if (status === Image.Loading)
                    root.artworkState = "loading"
                else if (status === Image.Error)
                    root.artworkState = root.coverUrl ? "error" : "missing"
            }

            Behavior on opacity {
                NumberAnimation {
                    duration: root.fadeDuration
                    easing.type: MichiTheme.motion.easing.entrance
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            visible: root.showPlaceholder && !root.ready
            color: MichiTheme.colors.surfaceSubtle

            Text {
                anchors.centerIn: parent
                text: root.placeholderText
                visible: text !== ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: Math.max(14, Math.min(width, height) * 0.18)
                font.weight: MichiTheme.typography.weightBold
                Accessible.ignored: true
            }

            MichiIcon {
                anchors.centerIn: parent
                size: Math.max(18, Math.min(parent.width, parent.height) * 0.24)
                iconName: "albums"
                visible: root.placeholderText === ""
                accessibleName: ""
                Accessible.ignored: true
            }
        }
    }

    Connections {
        target: typeof coverProviderBridge !== "undefined" ? coverProviderBridge : null
        function onCoverReady(key, url) {
            if (key === root.coverKey) {
                root.coverUrl = url || ""
                root.artworkState = url ? "loading" : "missing"
            }
        }
        function onCoverInvalidated(key) {
            if (key === root.coverKey) {
                root.coverUrl = ""
                root.artworkState = root.coverKey ? "loading" : "idle"
                Qt.callLater(root.refreshCover)
            }
        }
    }
}
