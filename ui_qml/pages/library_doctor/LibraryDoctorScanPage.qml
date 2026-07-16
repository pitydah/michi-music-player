import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Library Doctor Scan"
    objectName: "libraryDoctorScanPage"
    focus: true
    id: root

    property var doc: null

    Column {
        width: parent.width
        spacing: MichiTheme.spacing.sm

        SectionHeader { text: "Escaneo"; width: parent.width }

        GlassMaterial {
            width: parent.width; radius: MichiTheme.radiusMd; variant: "base"
            Column {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.md

                Text {
                    text: "Inicia un escaneo completo de la biblioteca para detectar problemas."
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap; width: parent.width
                }

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton {
                        text: root.doc && root.doc.status === "scanning" ? "Escaneando..." : "Escanear biblioteca"
                        variant: "primary"
                        onClicked: {
                            if (root.doc && typeof root.doc.scan !== "undefined")
                                root.doc.scan()
                        }
                    }
                    MichiButton {
                        text: "Cancelar escaneo"
                        variant: "ghost"
                        visible: root.doc && root.doc.status === "scanning"
                        onClicked: {
                            if (root.doc && typeof root.doc.cancelScan !== "undefined")
                                root.doc.cancelScan()
                        }
                    }
                }

                Row {
                    spacing: MichiTheme.spacing.sm; visible: root.doc && root.doc.status === "done"
                    Text { text: "Filtrar:"; color: MichiTheme.colors.textSecondary; anchors.verticalCenter: parent.verticalCenter }
                    TextField { id: filterField; width: 200; placeholderText: "Tipo de issue..." }
                        focusPolicy: Qt.StrongFocus
                }
            }
        }
    }
}
