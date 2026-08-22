import QtQuick
import QtQuick.Layouts
import "../components"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    property bool immersive: false
    spacing: MichiSpacing.lg

    Item { Layout.fillHeight: true }

    Artwork {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: Math.min(root.immersive ? 500 : 420,
                                        Math.max(280, root.width * (root.immersive ? 0.50 : 0.42)))
        Layout.preferredHeight: Layout.preferredWidth
        sourcePath: playback.artworkPath
        fallbackText: playback.title
        requestedSize: Math.round(width * Screen.devicePixelRatio)
        radius: MichiRadius.lg
    }

    ColumnLayout {
        Layout.alignment: Qt.AlignHCenter
        Layout.maximumWidth: 560
        spacing: MichiSpacing.xs
        MichiText {
            Layout.fillWidth: true
            text: playback.title || "Nothing playing"
            role: "title"
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: [playback.artist, playback.album].filter(value => value !== "").join(" · ")
            role: "secondary"
            horizontalAlignment: Text.AlignHCenter
            visible: text.length > 0
            elide: Text.ElideRight
        }
        MichiText {
            Layout.fillWidth: true
            text: playback.qualityLabel
            role: "technical"
            technical: true
            horizontalAlignment: Text.AlignHCenter
            visible: text.length > 0
        }
    }

    Item { Layout.fillHeight: true }
}
