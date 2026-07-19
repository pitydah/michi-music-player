import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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

        RowLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.lg

            CoverImage {
                Layout.alignment: Qt.AlignVCenter
                Layout.preferredWidth: 56
                Layout.preferredHeight: 56
                coverRadius: MichiTheme.radius.sm
                coverKey: root.hasPlayback ? "NOWPLAYING" : ""
                visible: root.hasPlayback
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Continuar escuchando")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasPlayback
                        ? (root.trackTitle + " · " + root.trackArtist)
                        : "No hay reproducción activa"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                }
            }

            MichiButton {
                Layout.alignment: Qt.AlignVCenter
                text: root.hasPlayback ? "Reproducir" : qsTr("Sin reproducción")
                variant: root.hasPlayback ? "accent" : "secondary"
                enabled: root.hasPlayback
                onClicked: root.activate()
            }
        }
    }
}
