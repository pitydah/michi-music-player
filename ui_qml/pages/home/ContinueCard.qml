import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Continue Card"
    objectName: "continueCard"
    focus: true
    id: root

    property string trackTitle: "—"
    property string trackArtist: "—"
    property bool hasPlayback: false

    signal activate()

    implicitHeight: MichiTheme.density.comfortable + MichiTheme.spacing.xl * 2

    Accessible.onPressAction: root.activate()

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radius.md

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.activate()
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            CoverImage {
                anchors.verticalCenter: parent.verticalCenter
                width: 56
                height: 56
                coverRadius: MichiTheme.radius.sm
                coverKey: root.hasPlayback ? "NOWPLAYING" : ""
                visible: root.hasPlayback
            }

            Column {
                width: parent.width - 160
                anchors.verticalCenter: parent.verticalCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    text: qsTr("Continuar escuchando")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: root.hasPlayback
                        ? (root.trackTitle + " · " + root.trackArtist)
                        : "No hay reproducción activa"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            MichiButton {
                anchors.verticalCenter: parent.verticalCenter
                text: root.hasPlayback ? "Reproducir" : qsTr("Sin reproducción")
                variant: root.hasPlayback ? "accent" : "secondary"
                enabled: root.hasPlayback
                onClicked: root.activate()
            }
        }
    }
}
