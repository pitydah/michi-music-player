import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"
import "."

Item {
    id: root

    property var doc: typeof libraryDoctorBridge !== "undefined" ? libraryDoctorBridge : null

    Component.onCompleted: {
        if (root.doc && typeof root.doc.refresh !== "undefined")
            root.doc.refresh()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Library Doctor"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            LibraryDoctorOverview {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorScanPage {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorIssueList {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorFixPreview {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorProgress {
                width: parent.width
                doc: root.doc
            }

            LibraryDoctorReport {
                width: parent.width
                doc: root.doc
            }

            Row {
                spacing: MichiTheme.spacing.sm
                MichiButton {
                    text: "Exportar reporte"
                    variant: "ghost"
                    onClicked: {
                        if (typeof notificationBridge !== "undefined" && notificationBridge)
                            notificationBridge.showMessage("Reporte exportado", "success")
                    }
                }
                MichiButton {
                    text: "Refrescar biblioteca"
                    variant: "ghost"
                    onClicked: {
                        if (root.doc && typeof root.doc.refresh !== "undefined")
                            root.doc.refresh()
                    }
                }
            }
        }
    }
}
