// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"
import "../../../../components"

Item {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property int trackCount: 0

    signal clicked()
    signal contextRequested(real x, real y)

    width: 150
    height: 180

    Item {
        anchors.centerIn: parent
        width: 120
        height: 130

        Rectangle {
            id: vinylDisc
            anchors.fill: parent
            radius: 60
            color: MichiTheme.colors.borderInner
            border.width: 2
            border.color: MichiTheme.colors.borderSubtle

            Rectangle {
                anchors.centerIn: parent
                width: 50
                height: 50
                radius: 25
                color: MichiTheme.colors.surfaceCard
                clip: true

                CoverImage {
                    anchors.fill: parent
                    anchors.margins: 2
                    coverRadius: 23
                    coverKey: root.albumKey || ""
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 10
                height: 10
                radius: 5
                color: MichiTheme.colors.borderInner
            }
        }

        Text {
            anchors.top: vinylDisc.bottom
            anchors.topMargin: MichiTheme.spacing.xs
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.albumTitle
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true
            onClicked: root.clicked()
            onPressAndHold: root.contextRequested(mouse.x, mouse.y)
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onEntered: {
                vinylDisc.rotation = 0
            }
            onExited: {
                vinylDisc.rotation = 0
            }
        }
    }
}
