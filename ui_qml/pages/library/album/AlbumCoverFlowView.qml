// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumCoverFlowView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("CoverFlow de álbumes")

    property var albumModel: null
    property var bridge: null
    property int coverSize: Math.max(190, Math.min(320, Math.min(width * 0.28, height * 0.48)))
    readonly property var currentAlbum: albumModel && albumModel.count > 0 && albumModel.get
                                        ? albumModel.get(pathView.currentIndex) : ({})
    signal albumClicked(string albumKey, string title, string artist, int year)

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceHero
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.surfaceHeroGlow }
                GradientStop { position: 0.58; color: "transparent" }
                GradientStop { position: 1.0; color: MichiTheme.colors.surfaceSubtle }
            }
        }
    }

    PathView {
        id: pathView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: detailsPanel.top
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        pathItemCount: width > 1100 ? 9 : width > 760 ? 7 : 5
        cacheItemCount: pathItemCount + 2
        dragMargin: 160
        preferredHighlightBegin: 0.5
        preferredHighlightEnd: 0.5
        highlightRangeMode: PathView.StrictlyEnforceRange
        snapMode: PathView.SnapToItem
        focus: true

        Keys.onLeftPressed: decrementCurrentIndex()
        Keys.onRightPressed: incrementCurrentIndex()
        Keys.onReturnPressed: root.albumClicked(root.currentAlbum.albumKey || "", root.currentAlbum.title || "",
                                                root.currentAlbum.artist || "", root.currentAlbum.year || 0)
        Keys.onEnterPressed: root.albumClicked(root.currentAlbum.albumKey || "", root.currentAlbum.title || "",
                                               root.currentAlbum.artist || "", root.currentAlbum.year || 0)
        Keys.onSpacePressed: {
            if (root.bridge && root.bridge.playAlbum)
                root.bridge.playAlbum(root.currentAlbum.albumKey || "")
        }

        path: Path {
            startX: -root.coverSize * 0.35
            startY: pathView.height * 0.58
            PathAttribute { name: "itemScale"; value: 0.56 }
            PathAttribute { name: "itemOpacity"; value: 0.28 }
            PathAttribute { name: "itemAngle"; value: -54 }
            PathAttribute { name: "itemDepth"; value: 0 }

            PathCurve { x: pathView.width * 0.24; y: pathView.height * 0.51 }
            PathAttribute { name: "itemScale"; value: 0.76 }
            PathAttribute { name: "itemOpacity"; value: 0.72 }
            PathAttribute { name: "itemAngle"; value: -30 }
            PathAttribute { name: "itemDepth"; value: 4 }

            PathCurve { x: pathView.width * 0.5; y: pathView.height * 0.46 }
            PathAttribute { name: "itemScale"; value: 1.08 }
            PathAttribute { name: "itemOpacity"; value: 1.0 }
            PathAttribute { name: "itemAngle"; value: 0 }
            PathAttribute { name: "itemDepth"; value: 12 }

            PathCurve { x: pathView.width * 0.76; y: pathView.height * 0.51 }
            PathAttribute { name: "itemScale"; value: 0.76 }
            PathAttribute { name: "itemOpacity"; value: 0.72 }
            PathAttribute { name: "itemAngle"; value: 30 }
            PathAttribute { name: "itemDepth"; value: 4 }

            PathCurve { x: pathView.width + root.coverSize * 0.35; y: pathView.height * 0.58 }
            PathAttribute { name: "itemScale"; value: 0.56 }
            PathAttribute { name: "itemOpacity"; value: 0.28 }
            PathAttribute { name: "itemAngle"; value: 54 }
            PathAttribute { name: "itemDepth"; value: 0 }
        }

        delegate: Item {
            id: flowItem
            width: root.coverSize
            height: root.coverSize * 1.22
            scale: PathView.isCurrentItem ? 1.08 : PathView.itemScale
            opacity: PathView.itemOpacity
            z: PathView.isCurrentItem ? 100 : PathView.itemDepth

            Accessible.role: Accessible.Button
            Accessible.name: (model.title || qsTr("Álbum sin título")) + " — " + (model.artist || "")
            Accessible.onPressAction: root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)

            Item {
                id: artContainer
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: root.coverSize
                height: root.coverSize

                transform: Rotation {
                    axis.y: 1
                    origin.x: artContainer.width / 2
                    origin.y: artContainer.height / 2
                    angle: PathView.isCurrentItem ? 0 : PathView.itemAngle
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: -6
                    radius: MichiTheme.radius.lg
                    color: PathView.isCurrentItem ? MichiTheme.colors.accentSoft : MichiTheme.colors.shadowSoft
                    opacity: PathView.isCurrentItem ? 0.9 : 0.5
                }

                CoverImage {
                    anchors.fill: parent
                    coverRadius: MichiTheme.radius.md
                    coverKey: model.coverKey || model.albumKey || ""
                }

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.bottom
                    height: root.coverSize * 0.28
                    opacity: PathView.isCurrentItem ? 0.26 : 0.12
                    scale: -1
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: MichiTheme.colors.textPrimary }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: MichiTheme.spacing.sm
                    width: 42; height: 42; radius: 21
                    color: MichiTheme.colors.accentPrimary
                    opacity: PathView.isCurrentItem ? 1 : 0
                    scale: PathView.isCurrentItem ? 1 : 0.8
                    Behavior on opacity { NumberAnimation { duration: MichiTheme.motionFast } }
                    Behavior on scale { NumberAnimation { duration: MichiTheme.motionFast } }
                    Text {
                        anchors.centerIn: parent
                        text: "▶"
                        color: MichiTheme.colors.textOnAccent
                        font.pixelSize: 15
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            if (root.bridge && root.bridge.playAlbum)
                                root.bridge.playAlbum(model.albumKey || "")
                        }
                    }
                }
            }

            Text {
                anchors.top: artContainer.bottom
                anchors.topMargin: MichiTheme.spacing.md
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width * 0.94
                horizontalAlignment: Text.AlignHCenter
                text: model.title || qsTr("Álbum sin título")
                color: PathView.isCurrentItem ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
                font.pixelSize: PathView.isCurrentItem ? MichiTheme.typography.sectionTitleSize : MichiTheme.typography.metaSize
                font.weight: PathView.isCurrentItem ? MichiTheme.typography.weightSemiBold : MichiTheme.typography.weightMedium
                elide: Text.ElideRight
            }

            MouseArea {
                anchors.fill: artContainer
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (!PathView.isCurrentItem)
                        pathView.currentIndex = index
                    else
                        root.albumClicked(model.albumKey || "", model.title || "", model.artist || "", model.year || 0)
                }
                onDoubleClicked: {
                    if (root.bridge && root.bridge.playAlbum)
                        root.bridge.playAlbum(model.albumKey || "")
                }
            }

            Behavior on scale { NumberAnimation { duration: MichiTheme.motionNormal; easing.type: Easing.OutCubic } }
            Behavior on opacity { NumberAnimation { duration: MichiTheme.motionNormal } }
        }
    }

    Rectangle {
        id: detailsPanel
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: MichiTheme.spacing.md
        height: 86
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceToolbar
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderCard
        visible: root.albumModel && root.albumModel.count > 0

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    Layout.fillWidth: true
                    text: root.currentAlbum.title || qsTr("Álbum sin título")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: (root.currentAlbum.artist || qsTr("Artista desconocido")) +
                          ((root.currentAlbum.year || 0) > 0 ? " · " + root.currentAlbum.year : "") +
                          " · " + (root.currentAlbum.trackCount || 0) + " " + qsTr("canciones")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }
            }

            Text {
                text: (pathView.currentIndex + 1) + " / " + pathView.count
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
            }

            MichiButton {
                text: qsTr("Reproducir")
                variant: "primary"
                onClicked: {
                    if (root.bridge && root.bridge.playAlbum)
                        root.bridge.playAlbum(root.currentAlbum.albumKey || "")
                }
            }
            MichiButton {
                text: qsTr("Abrir")
                variant: "ghost"
                onClicked: root.albumClicked(root.currentAlbum.albumKey || "", root.currentAlbum.title || "",
                                             root.currentAlbum.artist || "", root.currentAlbum.year || 0)
            }
        }
    }
}
