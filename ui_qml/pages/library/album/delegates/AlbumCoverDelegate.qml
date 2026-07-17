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
    signal doubleClicked()

    width: 160
    height: 200

    Rectangle {
        anchors.centerIn: parent
        width: 140
        height: 140
        radius: MichiTheme.radiusSm
        color: MichiTheme.colors.borderInner
        scale: PathView.isCurrentItem ? 1.15 : 0.80
        opacity: PathView.isCurrentItem ? 1.0 : 0.5
        z: PathView.isCurrentItem ? 10 : 1

        transform: Rotation {
            axis.y: 1
            origin.x: 70
            origin.y: 70
            angle: PathView.isCurrentItem ? 0 : (PathView.itemAngle || 0)
        }

        CoverImage {
            anchors.fill: parent
            coverRadius: MichiTheme.radiusSm
            coverKey: root.albumKey || ""
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
            onClicked: root.clicked()
            onDoubleClicked: root.doubleClicked()
        }
    }

    Text {
        anchors.top: parent.bottom
        anchors.topMargin: MichiTheme.spacing.sm
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: root.albumTitle
        color: PathView.isCurrentItem ? MichiTheme.colors.textPrimary : MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.metaSize
        font.weight: PathView.isCurrentItem ? MichiTheme.typography.weightMedium : MichiTheme.typography.weightNormal
        elide: Text.ElideRight
    }

    Text {
        anchors.top: parent.bottom
        anchors.topMargin: MichiTheme.spacing.sm + MichiTheme.spacing.xs + MichiTheme.typography.metaSize
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: root.albumArtist
        color: PathView.isCurrentItem ? MichiTheme.colors.textSecondary : MichiTheme.colors.textMuted
        font.pixelSize: MichiTheme.typography.captionSize
        opacity: PathView.isCurrentItem ? 1.0 : 0.6
        elide: Text.ElideRight
    }
}
