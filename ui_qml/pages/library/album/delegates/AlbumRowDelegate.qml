// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../../theme"
import "../../../../components"

Item {
    id: root

    property string albumKey: ""
    property string albumTitle: ""
    property string albumArtist: ""
    property int albumYear: 0
    property int trackCount: 0
    property int decade: 0

    signal clicked()
    signal contextRequested(real x, real y)

    width: parent ? parent.width : 200
    height: 48
    activeFocusOnTab: enabled

    Rectangle {
        anchors.fill: parent
        color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
        radius: MichiTheme.radiusXs

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.lg
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            CoverImage {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                coverRadius: MichiTheme.radiusXs
                coverKey: root.albumKey || ""
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: 0

                Text {
                    Layout.fillWidth: true
                    text: root.albumTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: root.albumArtist
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    visible: text !== ""
                }
            }

            Text {
                text: root.trackCount > 0 ? root.trackCount + " temas" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }

            Text {
                text: root.albumYear > 0 ? root.albumYear : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                visible: text !== ""
            }
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
            onPressAndHold: root.contextRequested(mouse.x, mouse.y)
            acceptedButtons: Qt.LeftButton | Qt.RightButton
        }
    }
}
