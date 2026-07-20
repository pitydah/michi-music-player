// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

Item {
    id: root
    objectName: "albumTimelineView"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Línea de tiempo de álbumes")
    Accessible.description: qsTr("Explora la colección por año o década")

    property var albumModel: null
    property var bridge: null
    property bool groupByDecade: false
    property bool automaticPagination: true
    signal albumClicked(string albumKey, string title, string artist, int year)

    function currentAlbum() {
        if (!root.albumModel || listView.currentIndex < 0 || !root.albumModel.get)
            return null
        return root.albumModel.get(listView.currentIndex)
    }

    function openCurrentAlbum() {
        var album = root.currentAlbum()
        if (album)
            root.albumClicked(
                album.albumKey || album.album_key || "",
                album.title || "",
                album.artist || "",
                album.year || 0
            )
    }

    function playCurrentAlbum() {
        var album = root.currentAlbum()
        var key = album ? (album.albumKey || album.album_key || "") : ""
        if (key && root.bridge && root.bridge.playAlbum)
            root.bridge.playAlbum(key)
    }

    function maybeFetchMore() {
        if (!root.automaticPagination || !root.albumModel || !root.albumModel.hasMore ||
                root.albumModel.loadingMore || listView.moving)
            return
        var remaining = listView.contentHeight - (listView.contentY + listView.height)
        if (remaining <= 360)
            root.albumModel.fetchMore()
    }

    function scrollToAlbum(albumKey) {
        if (!root.albumModel || !root.albumModel.get)
            return
        for (var i = 0; i < root.albumModel.count; i++) {
            var album = root.albumModel.get(i)
            if ((album.albumKey || album.album_key || "") === albumKey) {
                listView.currentIndex = i
                listView.positionViewAtIndex(i, ListView.Center)
                return
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.sm

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceCard
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.lg
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.md

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    Text {
                        Layout.fillWidth: true
                        text: root.groupByDecade
                              ? qsTr("Archivo por década")
                              : qsTr("Archivo por año")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightSemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Enter abre · espacio reproduce · doble clic abre")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    objectName: "timelineGroupingSelector"
                    Layout.preferredWidth: root.width < 720 ? 154 : 190
                    Layout.preferredHeight: 36
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceInput
                    border.width: MichiTheme.borderWidth
                    border.color: MichiTheme.colors.borderCard

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 2

                        Repeater {
                            model: [qsTr("Años"), qsTr("Décadas")]

                            Rectangle {
                                required property int index
                                required property string modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: MichiTheme.radius.sm
                                readonly property bool selected: (index === 1) === root.groupByDecade
                                color: selected
                                       ? MichiTheme.colors.accentSelection
                                       : groupingMouse.containsMouse
                                         ? MichiTheme.colors.surfaceHover
                                         : "transparent"

                                Accessible.role: Accessible.Button
                                Accessible.name: modelData
                                Accessible.checked: selected
                                Accessible.onPressAction: root.groupByDecade = index === 1

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: parent.selected
                                           ? MichiTheme.colors.accentBlue
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }

                                MouseArea {
                                    id: groupingMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.groupByDecade = index === 1
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: MichiTheme.radius.lg
            color: MichiTheme.colors.surfaceElevation0
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderSubtle
            clip: true

            ListView {
                id: listView
                objectName: "albumTimelineList"
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                model: root.albumModel
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                spacing: MichiTheme.spacing.xs
                activeFocusOnTab: true
                focus: true
                keyNavigationWraps: false
                cacheBuffer: 320

                section.property: root.groupByDecade ? "decade" : "year"
                section.criteria: ViewSection.FullString
                section.labelPositioning: ViewSection.CurrentLabelAtStart | ViewSection.InlineLabels

                onContentYChanged: paginationTimer.restart()
                onMovementEnded: root.maybeFetchMore()
                onCurrentIndexChanged: {
                    if (currentIndex >= 0) {
                        positionViewAtIndex(currentIndex, ListView.Contain)
                        if (root.albumModel && root.albumModel.hasMore &&
                                !root.albumModel.loadingMore &&
                                currentIndex >= Math.max(0, count - 5))
                            root.albumModel.fetchMore()
                    }
                }

                Keys.onReturnPressed: root.openCurrentAlbum()
                Keys.onEnterPressed: root.openCurrentAlbum()
                Keys.onSpacePressed: root.playCurrentAlbum()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Home) {
                        currentIndex = count > 0 ? 0 : -1
                        positionViewAtBeginning()
                        event.accepted = true
                    } else if (event.key === Qt.Key_End) {
                        currentIndex = count > 0 ? count - 1 : -1
                        positionViewAtEnd()
                        root.maybeFetchMore()
                        event.accepted = true
                    }
                }

                Timer {
                    id: paginationTimer
                    interval: 90
                    repeat: false
                    onTriggered: root.maybeFetchMore()
                }

                ScrollBar.vertical: ScrollBar {
                    width: 8
                    policy: ScrollBar.AsNeeded
                }

                section.delegate: Rectangle {
                    required property string section
                    width: listView.width
                    height: 52
                    radius: MichiTheme.radius.md
                    color: MichiTheme.colors.surfaceToolbar
                    border.width: MichiTheme.borderWidth
                    border.color: MichiTheme.colors.borderSubtle
                    z: 4

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.lg
                        anchors.rightMargin: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Rectangle {
                            Layout.preferredWidth: 10
                            Layout.preferredHeight: 10
                            radius: 5
                            color: MichiTheme.colors.accentPrimary
                        }

                        Text {
                            text: {
                                var numeric = Number(section)
                                if (!numeric)
                                    return qsTr("Fecha desconocida")
                                return root.groupByDecade ? numeric + "s" : numeric
                            }
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        Item { Layout.fillWidth: true }

                        Text {
                            text: root.groupByDecade ? qsTr("Década") : qsTr("Año")
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            font.capitalization: Font.AllUppercase
                        }
                    }
                }

                delegate: Item {
                    id: timelineRow
                    required property int index
                    required property string albumKey
                    required property string title
                    required property string artist
                    required property var year
                    required property var trackCount
                    required property string coverKey

                    width: listView.width
                    height: 84
                    readonly property bool selected: ListView.isCurrentItem

                    Accessible.role: Accessible.Button
                    Accessible.name: (timelineRow.year || qsTr("Sin año")) + ": " +
                                     (timelineRow.title || qsTr("Álbum sin título"))
                    Accessible.description: qsTr("Doble clic para abrir. Espacio para reproducir.")
                    Accessible.onPressAction: root.albumClicked(
                                                  timelineRow.albumKey,
                                                  timelineRow.title,
                                                  timelineRow.artist,
                                                  Number(timelineRow.year) || 0
                                              )

                    Rectangle {
                        x: 35
                        y: -MichiTheme.spacing.xs
                        width: 2
                        height: parent.height + MichiTheme.spacing.sm
                        color: MichiTheme.colors.borderCard
                    }

                    Rectangle {
                        x: 27
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18
                        height: 18
                        radius: 9
                        color: timelineRow.selected || rowMouse.containsMouse
                               ? MichiTheme.colors.accentPrimary
                               : MichiTheme.colors.surfaceElevation4
                        border.width: 3
                        border.color: MichiTheme.colors.bgContent
                    }

                    Rectangle {
                        id: rowSurface
                        anchors.left: parent.left
                        anchors.leftMargin: 58
                        anchors.right: parent.right
                        anchors.rightMargin: MichiTheme.spacing.sm
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        radius: MichiTheme.radius.md
                        color: timelineRow.selected
                               ? MichiTheme.colors.accentSelection
                               : rowMouse.containsMouse
                                 ? MichiTheme.colors.surfaceCardHover
                                 : MichiTheme.colors.surfaceCard
                        border.width: timelineRow.selected ? MichiTheme.borderWidth : 0
                        border.color: MichiTheme.colors.borderActive
                        clip: true

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            acceptedButtons: Qt.LeftButton
                            onPressed: listView.currentIndex = timelineRow.index
                            onDoubleClicked: root.albumClicked(
                                                 timelineRow.albumKey,
                                                 timelineRow.title,
                                                 timelineRow.artist,
                                                 Number(timelineRow.year) || 0
                                             )
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            spacing: MichiTheme.spacing.md

                            CoverImage {
                                Layout.preferredWidth: 62
                                Layout.preferredHeight: 62
                                coverRadius: MichiTheme.radius.sm
                                coverKey: timelineRow.coverKey || timelineRow.albumKey
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    Layout.fillWidth: true
                                    text: timelineRow.title || qsTr("Álbum sin título")
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.bodySize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: timelineRow.artist || qsTr("Artista desconocido")
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: qsTr("%1 canciones").arg(Number(timelineRow.trackCount) || 0)
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.captionSize
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 58
                                Layout.preferredHeight: 28
                                radius: MichiTheme.radius.pill
                                color: MichiTheme.colors.surfaceInput
                                visible: Number(timelineRow.year) > 0

                                Text {
                                    anchors.centerIn: parent
                                    text: Number(timelineRow.year) > 0 ? timelineRow.year : ""
                                    color: MichiTheme.colors.textNormal
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 38
                                Layout.preferredHeight: 38
                                radius: 19
                                color: playMouse.pressed
                                       ? MichiTheme.colors.accentSecondary
                                       : rowMouse.containsMouse || timelineRow.selected
                                         ? MichiTheme.colors.accentPrimary
                                         : MichiTheme.colors.surfaceElevation3

                                Accessible.role: Accessible.Button
                                Accessible.name: qsTr("Reproducir %1").arg(
                                                     timelineRow.title || qsTr("álbum")
                                                 )
                                Accessible.onPressAction: {
                                    if (root.bridge && root.bridge.playAlbum)
                                        root.bridge.playAlbum(timelineRow.albumKey)
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: "▶"
                                    color: rowMouse.containsMouse || timelineRow.selected
                                           ? MichiTheme.colors.textOnAccent
                                           : MichiTheme.colors.textSecondary
                                    font.pixelSize: 12
                                }

                                MouseArea {
                                    id: playMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        listView.currentIndex = timelineRow.index
                                        if (root.bridge && root.bridge.playAlbum)
                                            root.bridge.playAlbum(timelineRow.albumKey)
                                    }
                                }
                            }
                        }
                    }
                }

                footer: Item {
                    width: listView.width
                    height: root.albumModel && root.albumModel.hasMore
                            ? 48
                            : MichiTheme.spacing.md

                    MichiButton {
                        anchors.centerIn: parent
                        visible: root.albumModel && root.albumModel.hasMore
                        enabled: root.albumModel && !root.albumModel.loadingMore
                        text: root.albumModel && root.albumModel.loadingMore
                              ? qsTr("Cargando…")
                              : qsTr("Cargar más")
                        variant: "ghost"
                        onClicked: root.albumModel.fetchMore()
                    }
                }
            }
        }
    }
}
