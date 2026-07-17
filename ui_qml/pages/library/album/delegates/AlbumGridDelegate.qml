// SPDX-FileCopyrightText: 2016 Matthieu Gallien <matthieu_gallien@yahoo.fr>
//   Patrón: Grid delegate con cover + hover indicators (adaptado de KDE Elisa)
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"
import "../../../../components"

FocusScope {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property int trackCount: 0

    signal clicked()
    signal doubleClicked()
    signal contextRequested(real x, real y)

    implicitWidth: 176
    implicitHeight: 232
    activeFocusOnTab: enabled
    Accessible.role: Accessible.ListItem
    Accessible.name: albumTitle + (albumArtist !== "" ? ", " + albumArtist : "")

    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()

    Rectangle {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        color: hover.hovered ? MichiTheme.colors.surfaceHover : MichiTheme.colors.surfaceCard
        border.width: hover.hovered ? 1 : 0
        border.color: hover.hovered ? MichiTheme.colors.borderCard : "transparent"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.sm
            spacing: MichiTheme.spacing.xs

            CoverImage {
                id: cover
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - MichiTheme.spacing.sm
                height: width
                coverRadius: MichiTheme.coverRadius
                coverKey: root.albumKey || ""
            }

            Text {
                width: parent.width
                text: root.albumTitle
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightMedium
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Text {
                width: parent.width
                text: root.albumArtist + (root.albumYear > 0 ? " · " + root.albumYear : "")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Text {
                width: parent.width
                text: root.trackCount > 0 ? root.trackCount + " canciones" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.captionSize
                visible: text !== ""
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
            onDoubleClicked: root.doubleClicked()
            onPressAndHold: root.contextRequested(mouse.x, mouse.y)
            acceptedButtons: Qt.LeftButton | Qt.RightButton
        }

        HoverHandler { id: hover }
    }

    MichiFocusRing { control: root; controlRadius: MichiTheme.radiusMd }
}
