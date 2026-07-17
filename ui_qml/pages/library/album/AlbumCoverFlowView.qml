// SPDX-FileCopyrightText: 2011 Martin Grimme <martin.grimme _AT_ gmail.com>
//   Patrón: PathAttribute dimming + reflection para CoverFlow
//   (inspirado en Nemo Mobile qmlmusicplayer / Music Shelf)
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../theme"
import "../../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Album Cover Flow View"
    objectName: "albumCoverFlowView"
    focus: true
    id: root

    property var albumModel: null
    property var bridge: null
    property int coverSize: 140
    signal albumClicked(string albumKey, string title, string artist, int year)

    PathView {
        id: pathView
        anchors.fill: parent
        model: root.albumModel
        clip: true
        pathItemCount: 5
        cacheItemCount: 4
        dragMargin: 100
        preferredHighlightBegin: 0.5
        preferredHighlightEnd: 0.5
        highlightRangeMode: PathView.StrictlyEnforceRange
        snapMode: PathView.SnapToItem
        focus: true

        Keys.onLeftPressed: decrementCurrentIndex()
        Keys.onRightPressed: incrementCurrentIndex()

        path: Path {
            id: coverflowPath
            startX: -100
            startY: pathView.height / 2
            PathAttribute { name: "itemScale"; value: 0.70 }
            PathAttribute { name: "itemOpacity"; value: 0.50 }
            PathAttribute { name: "itemAngle"; value: -25 }
            PathAttribute { name: "zValue"; value: 1 }

            PathLine { x: pathView.width / 2; y: pathView.height / 2 }
            PathAttribute { name: "itemScale"; value: 1.15 }
            PathAttribute { name: "itemOpacity"; value: 1.0 }
            PathAttribute { name: "itemAngle"; value: 0 }
            PathAttribute { name: "zValue"; value: 10 }

            PathLine { x: pathView.width + 100; y: pathView.height / 2 }
            PathAttribute { name: "itemScale"; value: 0.70 }
            PathAttribute { name: "itemOpacity"; value: 0.50 }
            PathAttribute { name: "itemAngle"; value: 25 }
            PathAttribute { name: "zValue"; value: 1 }
        }

        delegate: Item {
            width: 160
            height: 200

            Rectangle {
                anchors.centerIn: parent
                width: root.coverSize
                height: root.coverSize
                radius: MichiTheme.radiusSm
                color: MichiTheme.colors.borderInner
                scale: PathView.isCurrentItem ? 1.15 : PathView.itemScale
                opacity: PathView.itemOpacity
                z: PathView.zValue

                transform: Rotation {
                    axis.y: 1
                    origin.x: root.coverSize / 2
                    origin.y: root.coverSize / 2
                    angle: PathView.isCurrentItem ? 0 : PathView.itemAngle
                }

                CoverImage {
                    anchors.fill: parent
                    coverRadius: MichiTheme.radiusSm
                    coverKey: model.albumKey || ""
                }

                Behavior on scale {
                    NumberAnimation { duration: MichiTheme.motionNormal; easing.type: Easing.OutCubic }
                }
                Behavior on opacity {
                    NumberAnimation { duration: MichiTheme.motionNormal; easing.type: Easing.OutCubic }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                    onDoubleClicked: {
                        if (root.bridge && root.bridge.playAlbum) {
                            root.bridge.playAlbum(model.albumKey || "")
                        }
                    }
                }
            }

            Text {
                anchors.top: parent.bottom
                anchors.topMargin: MichiTheme.spacing.sm
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: model.title || ""
                color: PathView.isCurrentItem ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                font.weight: PathView.isCurrentItem ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
                elide: Text.ElideRight
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width * 0.3, 300)
        height: 4
        radius: 2
        color: MichiTheme.colors.borderSubtle
        visible: root.albumModel && root.albumModel.count > 0

        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            x: (pathView.currentIndex / Math.max(1, pathView.count - 1)) * (parent.width - parent.height)
            width: parent.height
            radius: 2
            color: MichiTheme.colors.accentBlue
        }
    }
}
