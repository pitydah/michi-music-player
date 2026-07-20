import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Rectangle {
    id: root
    objectName: "artistCard"
    focus: true

    property string artistName: ""
    property int trackCount: 0
    property int albumCount: 0
    property string coverKey: ""
    property bool selected: false

    signal clicked()

    radius: MichiTheme.radius.lg
    color: root.selected
           ? MichiTheme.colors.accentSelection
           : mouseArea.containsMouse
             ? MichiTheme.colors.surfaceCardHover
             : MichiTheme.colors.surfaceCard
    border.width: root.selected
                  ? MichiTheme.borderWidthFocus
                  : MichiTheme.borderWidth
    border.color: root.selected
                  ? MichiTheme.colors.borderFocus
                  : mouseArea.containsMouse
                    ? MichiTheme.colors.borderHover
                    : MichiTheme.colors.borderCard
    scale: mouseArea.pressed ? 0.985 : mouseArea.containsMouse ? 1.012 : 1.0
    clip: true

    Accessible.role: Accessible.Button
    Accessible.name: root.artistName || qsTr("Artista desconocido")
    Accessible.description: qsTr("%1 álbumes y %2 canciones")
                            .arg(root.albumCount)
                            .arg(root.trackCount)
    Accessible.onPressAction: root.clicked()

    Behavior on color {
        ColorAnimation { duration: MichiTheme.motionFast }
    }
    Behavior on border.color {
        ColorAnimation { duration: MichiTheme.motionFast }
    }
    Behavior on scale {
        NumberAnimation {
            duration: MichiTheme.motionFast
            easing.type: Easing.OutCubic
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.sm

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 108

            Rectangle {
                id: portrait
                width: Math.min(parent.width, parent.height)
                height: width
                anchors.centerIn: parent
                radius: width / 2
                color: MichiTheme.colors.surfaceElevation3
                border.width: MichiTheme.borderWidth
                border.color: root.selected
                              ? MichiTheme.colors.borderFocus
                              : MichiTheme.colors.borderCard
                clip: true

                CoverImage {
                    anchors.fill: parent
                    coverRadius: portrait.radius
                    coverKey: root.coverKey
                    visible: root.coverKey !== ""
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.coverKey === ""
                    text: root.artistName.length > 0
                          ? root.artistName.charAt(0).toUpperCase()
                          : qsTr("?")
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: Math.max(
                                        MichiTheme.typography.displaySize,
                                        portrait.width * 0.32
                                    )
                    font.weight: MichiTheme.typography.weightBold
                    opacity: 0.72
                }

                Rectangle {
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.08)
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.artistName || qsTr("Artista desconocido")
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            font.weight: MichiTheme.typography.weightSemiBold
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        Text {
            Layout.fillWidth: true
            text: qsTr("%1 álbumes · %2 canciones")
                  .arg(root.albumCount)
                  .arg(root.trackCount)
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.captionSize
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    ToolTip.visible: mouseArea.containsMouse
    ToolTip.delay: 700
    ToolTip.text: qsTr("Abrir artista")
}
