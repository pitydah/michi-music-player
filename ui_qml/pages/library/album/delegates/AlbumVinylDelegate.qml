// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import "../../../../theme"
import "../../../../components"
import "../components"

Item {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property int trackCount: 0
    property string qualityKind: ""
    property int sampleRate: 0
    property int bitDepth: 0

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
            border.color: hover.hovered ? MichiTheme.colors.accentBlue : MichiTheme.colors.borderSubtle
            Behavior on border.color {
                ColorAnimation { duration: MichiTheme.motionNormal; easing.type: Easing.OutQuad }
            }

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

            AlbumQualityBadge {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.topMargin: 4
                anchors.rightMargin: 4
                qualityKind: root.qualityKind
                sampleRate: root.sampleRate
                bitDepth: root.bitDepth
            }
        }

        Text {
            anchors.top: vinylDisc.bottom
            anchors.topMargin: MichiTheme.spacing.xs
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.albumTitle
            color: root.albumArtist !== "" ? MichiTheme.colors.textPrimary : MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            elide: Text.ElideRight
        }

        Text {
            anchors.top: vinylDisc.bottom
            anchors.topMargin: MichiTheme.spacing.sm + MichiTheme.typography.metaSize
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: root.albumArtist
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.captionSize
            elide: Text.ElideRight
            visible: text !== ""
        }

        HoverHandler { id: hover }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true
            onClicked: root.clicked()
            onPressAndHold: root.contextRequested(mouse.x, mouse.y)
            acceptedButtons: Qt.LeftButton | Qt.RightButton
        }

        NumberAnimation on rotation {
            id: vinylSpin
            running: hover.hovered
            loops: Animation.Infinite
            from: 0
            to: 360
            duration: 4000
        }
    }
}
