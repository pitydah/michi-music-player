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
    property var _pendingAlbum: ({})
    property int coverSize: Math.max(
        176,
        Math.min(300, Math.min(width * 0.235, height * 0.44))
    )
    readonly property var currentAlbum: albumModel && albumModel.count > 0 && albumModel.get
                                        ? albumModel.get(Math.max(0, Math.min(pathView.currentIndex, albumModel.count - 1)))
                                        : ({})

    signal albumClicked(string albumKey, string title, string artist, int year)

    function albumKeyOf(album) {
        return album ? (album.albumKey || album.album_key || "") : ""
    }

    function albumTitleOf(album) {
        return album ? (album.title || "") : ""
    }

    function albumArtistOf(album) {
        return album ? (album.artist || album.album_artist || "") : ""
    }

    function albumYearOf(album) {
        return album ? (album.year || 0) : 0
    }

    function albumTrackCountOf(album) {
        return album ? (album.trackCount || album.track_count || 0) : 0
    }

    function openCurrent() {
        const key = root.albumKeyOf(root.currentAlbum)
        if (!key)
            return
        root.albumClicked(
            key,
            root.albumTitleOf(root.currentAlbum),
            root.albumArtistOf(root.currentAlbum),
            root.albumYearOf(root.currentAlbum)
        )
    }

    function playCurrent() {
        const key = root.albumKeyOf(root.currentAlbum)
        if (root.bridge && root.bridge.playAlbum && key)
            root.bridge.playAlbum(key)
    }

    function scheduleOpen(key, title, artist, year) {
        root._pendingAlbum = { key: key, title: title, artist: artist, year: year }
        openTimer.restart()
    }

    Timer {
        id: openTimer
        interval: Qt.styleHints.mouseDoubleClickInterval
        onTriggered: root.albumClicked(
            root._pendingAlbum.key || "",
            root._pendingAlbum.title || "",
            root._pendingAlbum.artist || "",
            root._pendingAlbum.year || 0
        )
    }

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.surfaceHero
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.borderSubtle

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.58
            height: parent.height * 0.72
            radius: Math.min(width, height) / 2
            color: MichiTheme.colors.accentSoft
            opacity: 0.09
        }
    }

    PathView {
        id: pathView
        objectName: "albumCoverFlowPathView"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: detailsPanel.top
        anchors.margins: MichiTheme.spacing.md
        model: root.albumModel
        clip: true
        interactive: count > 1
        pathItemCount: width >= 1200 ? 7 : 5
        cacheItemCount: pathItemCount + 2
        dragMargin: Math.min(180, width * 0.18)
        preferredHighlightBegin: 0.5
        preferredHighlightEnd: 0.5
        highlightRangeMode: PathView.StrictlyEnforceRange
        snapMode: PathView.SnapToItem
        focus: true

        Keys.onPressed: function(event) {
            switch (event.key) {
            case Qt.Key_Left:
                pathView.decrementCurrentIndex()
                event.accepted = true
                break
            case Qt.Key_Right:
                pathView.incrementCurrentIndex()
                event.accepted = true
                break
            case Qt.Key_Home:
                pathView.currentIndex = 0
                event.accepted = true
                break
            case Qt.Key_End:
                pathView.currentIndex = Math.max(0, pathView.count - 1)
                event.accepted = true
                break
            case Qt.Key_Return:
            case Qt.Key_Enter:
                root.openCurrent()
                event.accepted = true
                break
            case Qt.Key_Space:
                root.playCurrent()
                event.accepted = true
                break
            }
        }

        onCurrentIndexChanged: {
            if (root.albumModel && root.albumModel.hasMore && !root.albumModel.loadingMore
                    && currentIndex >= Math.max(0, count - 3))
                root.albumModel.fetchMore()
        }

        path: Path {
            startX: -root.coverSize * 0.18
            startY: pathView.height * 0.60
            PathAttribute { name: "itemScale"; value: 0.54 }
            PathAttribute { name: "itemOpacity"; value: 0.16 }
            PathAttribute { name: "itemAngle"; value: -58 }
            PathAttribute { name: "itemDepth"; value: 0 }

            PathCurve {
                x: pathView.width * 0.19
                y: pathView.height * 0.54
            }
            PathAttribute { name: "itemScale"; value: 0.72 }
            PathAttribute { name: "itemOpacity"; value: 0.62 }
            PathAttribute { name: "itemAngle"; value: -34 }
            PathAttribute { name: "itemDepth"; value: 30 }

            PathCurve {
                x: pathView.width * 0.50
                y: pathView.height * 0.45
            }
            PathAttribute { name: "itemScale"; value: 1.0 }
            PathAttribute { name: "itemOpacity"; value: 1.0 }
            PathAttribute { name: "itemAngle"; value: 0 }
            PathAttribute { name: "itemDepth"; value: 100 }

            PathCurve {
                x: pathView.width * 0.81
                y: pathView.height * 0.54
            }
            PathAttribute { name: "itemScale"; value: 0.72 }
            PathAttribute { name: "itemOpacity"; value: 0.62 }
            PathAttribute { name: "itemAngle"; value: 34 }
            PathAttribute { name: "itemDepth"; value: 30 }

            PathCurve {
                x: pathView.width + root.coverSize * 0.18
                y: pathView.height * 0.60
            }
            PathAttribute { name: "itemScale"; value: 0.54 }
            PathAttribute { name: "itemOpacity"; value: 0.16 }
            PathAttribute { name: "itemAngle"; value: 58 }
            PathAttribute { name: "itemDepth"; value: 0 }
        }

        delegate: Item {
            id: flowItem

            required property int index
            required property string albumKey
            required property string title
            required property string artist
            required property var year
            required property string coverKey

            width: root.coverSize
            height: root.coverSize * 1.18
            scale: PathView.isCurrentItem ? 1.04 : (PathView.itemScale || 0.54)
            opacity: PathView.itemOpacity === undefined ? 1 : PathView.itemOpacity
            z: PathView.isCurrentItem ? 1000 : Math.round(PathView.itemDepth || 0)

            Accessible.role: Accessible.Button
            Accessible.name: (flowItem.title || qsTr("Álbum sin título"))
                             + " — " + (flowItem.artist || "")
            Accessible.description: PathView.isCurrentItem
                                    ? qsTr("Álbum seleccionado. Enter para abrir, espacio para reproducir")
                                    : qsTr("Seleccionar álbum")
            Accessible.onPressAction: {
                if (PathView.isCurrentItem)
                    root.openCurrent()
                else
                    pathView.currentIndex = flowItem.index
            }

            Item {
                id: artContainer
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: root.coverSize
                height: root.coverSize

                transform: Rotation {
                    axis.x: 0
                    axis.y: 1
                    axis.z: 0
                    origin.x: artContainer.width / 2
                    origin.y: artContainer.height / 2
                    angle: PathView.isCurrentItem ? 0 : (PathView.itemAngle || 0)
                }

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: PathView.isCurrentItem ? -7 : -3
                    radius: MichiTheme.radius.lg
                    color: PathView.isCurrentItem
                           ? MichiTheme.colors.accentSoft
                           : MichiTheme.colors.shadowSoft
                    opacity: PathView.isCurrentItem ? 0.82 : 0.38
                }

                CoverImage {
                    anchors.fill: parent
                    coverRadius: MichiTheme.radius.md
                    coverKey: flowItem.coverKey || flowItem.albumKey || ""
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: MichiTheme.spacing.sm
                    width: 42
                    height: 42
                    radius: 21
                    color: MichiTheme.colors.accentPrimary
                    opacity: PathView.isCurrentItem ? 1 : 0
                    scale: PathView.isCurrentItem ? 1 : 0.86

                    Behavior on opacity {
                        NumberAnimation { duration: MichiTheme.motionFast }
                    }
                    Behavior on scale {
                        NumberAnimation { duration: MichiTheme.motionFast }
                    }

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
                                root.bridge.playAlbum(flowItem.albumKey || "")
                        }
                    }
                }
            }

            Rectangle {
                anchors.top: artContainer.bottom
                anchors.topMargin: 7
                anchors.horizontalCenter: parent.horizontalCenter
                width: artContainer.width * 0.64
                height: 10
                radius: 5
                color: MichiTheme.colors.shadowSoft
                opacity: PathView.isCurrentItem ? 0.44 : 0.22
                scale: PathView.isCurrentItem ? 1 : 0.76
            }

            Text {
                anchors.top: artContainer.bottom
                anchors.topMargin: MichiTheme.spacing.lg
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width * 0.94
                horizontalAlignment: Text.AlignHCenter
                text: flowItem.title || qsTr("Álbum sin título")
                color: PathView.isCurrentItem
                       ? MichiTheme.colors.textPrimary
                       : MichiTheme.colors.textMuted
                font.pixelSize: PathView.isCurrentItem
                                ? MichiTheme.typography.sectionTitleSize
                                : MichiTheme.typography.metaSize
                font.weight: PathView.isCurrentItem
                             ? MichiTheme.typography.weightSemiBold
                             : MichiTheme.typography.weightMedium
                elide: Text.ElideRight
            }

            MouseArea {
                anchors.fill: artContainer
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (!PathView.isCurrentItem)
                        pathView.currentIndex = flowItem.index
                    else
                        root.scheduleOpen(
                            flowItem.albumKey || "",
                            flowItem.title || "",
                            flowItem.artist || "",
                            flowItem.year || 0
                        )
                }
                onDoubleClicked: {
                    openTimer.stop()
                    if (root.bridge && root.bridge.playAlbum)
                        root.bridge.playAlbum(flowItem.albumKey || "")
                }
            }

            Behavior on scale {
                NumberAnimation {
                    duration: MichiTheme.motionNormal
                    easing.type: Easing.OutCubic
                }
            }
            Behavior on opacity {
                NumberAnimation { duration: MichiTheme.motionNormal }
            }
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
                    text: root.albumTitleOf(root.currentAlbum) || qsTr("Álbum sin título")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: (root.albumArtistOf(root.currentAlbum) || qsTr("Artista desconocido"))
                          + (root.albumYearOf(root.currentAlbum) > 0
                             ? " · " + root.albumYearOf(root.currentAlbum) : "")
                          + " · " + root.albumTrackCountOf(root.currentAlbum)
                          + " " + qsTr("canciones")
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
                onClicked: root.playCurrent()
            }

            MichiButton {
                text: qsTr("Abrir")
                variant: "ghost"
                onClicked: root.openCurrent()
            }
        }
    }
}
