import QtQuick
import QtQuick.Layouts
import "../../controls"
import "../../primitives"
import "../../theme"

// Dashboard hero: Michi Home summary + management entry (master pass §35).
// States: no Home · locked · unlocked (counts, pending, empty devices).
// No playback controls live here: Ecosystem is infrastructure only.
MichiGlassSurface {
    id: root
    objectName: "homeHeroCard"
    implicitHeight: content.implicitHeight + MichiSpacing.lg * 2

    signal manageRequested()

    RowLayout {
        id: content
        anchors.fill: parent
        anchors.margins: MichiSpacing.lg
        spacing: MichiSpacing.md

        ColumnLayout {
            Layout.fillWidth: true
            spacing: MichiSpacing.xxs

            MichiText {
                text: qsTr("Michi Home")
                role: "section"
            }
            MichiText {
                Layout.fillWidth: true
                text: !home.configured
                    ? qsTr("Sin Home configurado: tus dispositivos Michi "
                        + "pueden compartir identidad, configuración y "
                        + "confianza en tu red local.")
                    : (home.locked
                       ? qsTr("%1 está bloqueado. Desbloquealo para "
                              + "administrar tus dispositivos.")
                             .arg(home.homeName)
                       : qsTr("Dispositivos: %1 · Activos: %2 · Pendientes: %3")
                             .arg(home.deviceCount)
                             .arg(home.activeDeviceCount)
                             .arg(home.pendingDeviceCount))
                role: home.configured ? "body" : "secondary"
                wrapMode: Text.WordWrap
            }
            MichiText {
                visible: home.configured && !home.locked
                    && home.deviceCount === 0
                text: qsTr("Todavía no hay dispositivos. Crea tu primer "
                    + "Music Stream desde Fábrica.")
                role: "secondary"
            }
        }

        MichiStatusChip {
            visible: home.configured
            text: home.locked ? qsTr("Bloqueado") : qsTr("Desbloqueado")
            tone: home.locked ? "warning" : "active"
        }
        MichiStatusChip {
            visible: home.configured && !home.locked
                && home.pendingDeviceCount > 0
            text: qsTr("%1 pendientes").arg(home.pendingDeviceCount)
            tone: "warning"
        }

        MichiButton {
            text: home.configured ? qsTr("Administrar Home")
                                  : qsTr("Crear Michi Home")
            onClicked: root.manageRequested()
        }
    }
}
