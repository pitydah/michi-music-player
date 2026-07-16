import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Progress"
    objectName: "libraryDoctorProgress"
    focus: true
    id: root

    property var doc: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd
            variant: root.doc && root.doc.status === "scanning" ? "accent" :
                     root.doc && root.doc.status === "repairing" ? "danger" : "base"
            visible: root.doc && (root.doc.status === "scanning" || root.doc.status === "repairing")

            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm

                Text {
                    text: root.doc && root.doc.status === "scanning" ? "Escaneando biblioteca..." : "Reparando problemas..."
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                MichiProgressBar {
                    Accessible.role: Accessible.ProgressBar

                    activeFocusOnTab: true

                    width: parent.width
                    indeterminate: true
                }

                StatusBadge {
                    text: root.doc && root.doc.status === "scanning" ? "Revisando archivos de música..." :
                          root.doc && root.doc.status === "repairing" ? "Aplicando correcciones..." : ""
                    kind: "warning"
                }
            }
        }
    }
}
