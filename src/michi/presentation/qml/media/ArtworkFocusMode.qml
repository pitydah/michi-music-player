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

    Item {
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: Math.min(root.immersive ? 500 : 420,
                                        Math.max(280, root.width * (root.immersive ? 0.50 : 0.42)))
        Layout.preferredHeight: Layout.preferredWidth

        // Soft ambient bloom behind artwork
        Rectangle {
            anchors.centerIn: parent
            width: parent.width + 32
            height: parent.height + 32
            radius: MichiRadius.floating + 2
            color: MichiSemanticColors.contentAmbientBlue
            opacity: 0.45
            z: -1
        }

        Artwork {
            anchors.fill: parent
            sourcePath: playback.artworkPath
            fallbackText: playback.title
            requestedSize: Math.round(width * Screen.devicePixelRatio)
            radius: MichiRadius.lg
        }
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
        Rectangle {
            visible: (playback.qualityLabel && playback.qualityLabel.length > 0) || false
            Layout.alignment: Qt.AlignHCenter
            implicitHeight: 28
            implicitWidth: qualityTextItem.implicitWidth + MichiSpacing.lg * 2
            radius: 14
            color: MichiSemanticColors.auroraPurpleSurfaceSoft
            border.width: 1
            border.color: MichiSemanticColors.auroraPurpleBorderMedium

            RowLayout {
                anchors.centerIn: parent
                spacing: MichiSpacing.xs
                Rectangle {
                    width: 6
                    height: 6
                    radius: 3
                    color: MichiPalette.auroraGreen
                }
                MichiText {
                    id: qualityTextItem
                    text: playback.qualityLabel || ""
                    role: "technical"
                    technical: true
                    color: MichiPalette.textPrimary
                    font.weight: Font.DemiBold
                }
            }
        }
    }

    Item { Layout.fillHeight: true }
}
