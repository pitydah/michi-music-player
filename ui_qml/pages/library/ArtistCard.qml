import QtQuick
import QtQuick.Controls
import MichiCover 1.0
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string artistName: ""
    property int trackCount: 0
    property int albumCount: 0
    property string coverId: ""

    signal clicked()

    implicitWidth: 180
    implicitHeight: 200

    GlassMaterial {
        anchors.fill: parent
        radius: 12
        hovered: mouseArea.containsMouse
        interactive: true

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.clicked()
        }

        Column {
            anchors.fill: parent
            anchors.margins: MichiSpacing.md
            spacing: MichiSpacing.sm

            Rectangle {
                width: parent.width
                height: width
                radius: width / 2
                color: Qt.rgba(1.0, 1.0, 1.0, 0.03)
                clip: true

                CoverBridge {
                    anchors.fill: parent
                    coverKey: root.coverId || root.artistName || "ARTIST"
                }

                Text {
                    anchors.centerIn: parent
                    text: root.artistName ? root.artistName.charAt(0).toUpperCase() : "?"
                    color: MichiColors.accentBlue
                    font.pixelSize: 32
                    font.weight: MichiTypography.weightBold
                    visible: !root.coverId && parent.source === ""
                }
            }

            Text {
                text: root.artistName
                color: MichiColors.textPrimary
                font.pixelSize: MichiTypography.cardTitleSize
                font.weight: MichiTypography.weightSemiBold
                elide: Text.ElideRight
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                text: root.albumCount > 0 ? root.albumCount + " álbumes" : ""
                color: MichiColors.textMuted
                font.pixelSize: MichiTypography.metaSize
                horizontalAlignment: Text.AlignHCenter
                width: parent.width
            }
        }
    }
}
