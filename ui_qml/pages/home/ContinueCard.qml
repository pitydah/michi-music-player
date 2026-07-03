import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../materials"
import "../../components"

Item {
    id: root

    property string trackTitle: "—"
    property string trackArtist: "—"
    property bool hasPlayback: false

    implicitHeight: 100

    GlassMaterial {
        anchors.fill: parent
        hovered: mouseArea.containsMouse
        interactive: true
        radius: MichiTheme.radiusMd

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
        }

        Row {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            Column {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 140
                spacing: MichiTheme.spacing.xs

                Text {
                    text: "Continuar escuchando"
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
                text: root.hasPlayback ? "Reproducir" : "Sin reproducción"
                variant: root.hasPlayback ? "accent" : "secondary"
                enabled: root.hasPlayback
            }
        }
    }
}
