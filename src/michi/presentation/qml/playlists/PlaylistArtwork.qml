import QtQuick
import QtQuick.Layouts
import "../media"
import "../primitives"
import "../theme"

Item {
    id: root

    property string customCoverPath: ""
    property var mosaicArtworkPaths: []
    property string fallbackText: "P"
    property real radius: MichiRadius.md

    implicitWidth: 120
    implicitHeight: 120

    Rectangle {
        id: bgContainer
        anchors.fill: parent
        radius: root.radius
        color: MichiPalette.obsidianDeep
        clip: true

        // Case 1: Custom Cover
        Artwork {
            anchors.fill: parent
            visible: root.customCoverPath !== ""
            sourcePath: root.customCoverPath
            radius: root.radius
            requestedSize: Math.round(Math.max(root.width, root.height) * Screen.devicePixelRatio)
        }

        // Case 2: Mosaic of 4
        Grid {
            anchors.fill: parent
            columns: 2
            rows: 2
            spacing: 1
            visible: root.customCoverPath === "" && root.mosaicArtworkPaths && root.mosaicArtworkPaths.length >= 4

            Repeater {
                model: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length >= 4) ? root.mosaicArtworkPaths.slice(0, 4) : []
                Artwork {
                    width: (bgContainer.width - 1) / 2
                    height: (bgContainer.height - 1) / 2
                    sourcePath: modelData
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
                }
            }
        }

        // Case 3: Mosaic of 3 (1 large left, 2 stacked right)
        RowLayout {
            anchors.fill: parent
            spacing: 1
            visible: root.customCoverPath === "" && root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 3

            Artwork {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 3) ? root.mosaicArtworkPaths[0] : ""
                requestedSize: Math.round(width * Screen.devicePixelRatio)
            }

            ColumnLayout {
                Layout.preferredWidth: parent.width / 2
                Layout.fillHeight: true
                spacing: 1

                Artwork {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 3) ? root.mosaicArtworkPaths[1] : ""
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
                }
                Artwork {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 3) ? root.mosaicArtworkPaths[2] : ""
                    requestedSize: Math.round(width * Screen.devicePixelRatio)
                }
            }
        }

        // Case 4: Mosaic of 2 (Left & Right)
        RowLayout {
            anchors.fill: parent
            spacing: 1
            visible: root.customCoverPath === "" && root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 2

            Artwork {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 2) ? root.mosaicArtworkPaths[0] : ""
                requestedSize: Math.round(width * Screen.devicePixelRatio)
            }
            Artwork {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 2) ? root.mosaicArtworkPaths[1] : ""
                requestedSize: Math.round(width * Screen.devicePixelRatio)
            }
        }

        // Case 5: Single Artwork
        Artwork {
            anchors.fill: parent
            visible: root.customCoverPath === "" && root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 1
            sourcePath: (root.mosaicArtworkPaths && root.mosaicArtworkPaths.length === 1) ? root.mosaicArtworkPaths[0] : ""
            radius: root.radius
            requestedSize: Math.round(Math.max(root.width, root.height) * Screen.devicePixelRatio)
        }

        // Case 6: Fallback (Empty / 0 tracks or no embedded covers)
        Rectangle {
            anchors.fill: parent
            visible: root.customCoverPath === "" && (!root.mosaicArtworkPaths || root.mosaicArtworkPaths.length === 0)
            radius: root.radius
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0; color: MichiPalette.playerSurfaceTop }
                GradientStop { position: 1; color: MichiPalette.obsidianDeep }
            }
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle

            // Large subtle initial monogram in background
            MichiText {
                anchors.centerIn: parent
                text: root.fallbackText.length > 0 ? root.fallbackText.charAt(0).toUpperCase() : "P"
                font.pixelSize: Math.round(root.width * 0.48)
                font.weight: Font.Bold
                color: MichiSemanticColors.innerHighlight
                opacity: 0.25
                visible: root.width >= 80
            }

            // Clean playlist icon in center
            MichiIcon {
                anchors.centerIn: parent
                width: Math.min(root.width * 0.36, 40)
                height: width
                name: "playlist"
                strokeWidth: 1.5
                iconColor: MichiPalette.auroraCyan
            }
        }

        // Inner physical perimeter frame
        Rectangle {
            anchors.fill: parent
            radius: root.radius
            color: "transparent"
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
        }
    }
}
