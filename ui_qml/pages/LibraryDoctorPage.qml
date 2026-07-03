import QtQuick
import QtQuick.Controls
import "../theme"
import "../components"
import "../materials"

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

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radiusLg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text { text: "Diagnóstico de biblioteca"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                    Text { text: "Analiza y detecta problemas en tu colección musical."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.80; wrapMode: Text.WordWrap }
                }
            }

            Row {
                spacing: MichiTheme.spacing.md
                Text { text: "Estado:"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter }
                StatusBadge {
                    text: root.doc ? root.doc.status : "idle"
                    kind: root.doc && root.doc.status === "done" ? "success" : root.doc && root.doc.status === "scanning" ? "warning" : "info"
                }
            }

            Row {
                spacing: MichiTheme.spacing.md
                visible: root.doc && root.doc.status === "done"
                Text { text: "Revisados: " + (root.doc ? root.doc.totalChecked : 0); color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize }
                Text { text: "Problemas: " + (root.doc ? root.doc.issueCount : 0); color: MichiTheme.colors.warning; font.pixelSize: MichiTheme.typography.bodySize }
            }

            SectionHeader { text: "Problemas detectados"; width: parent.width }

            Repeater {
                model: root.doc ? root.doc.issues : []

                GlassMaterial {
                    width: parent.width; height: 48; radius: MichiTheme.radiusSm; variant: root.doc && root.doc.issueCount > 0 ? "danger" : "base"
                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { width: parent.width * 0.30; text: modelData.type || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium; anchors.verticalCenter: parent.verticalCenter }
                        Text { width: parent.width * 0.60; text: modelData.detail || ""; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            Text {
                text: root.doc && root.doc.issues.length === 0 ? (root.doc.status === "idle" ? "Presiona \"Escanear\" para comenzar." : "No se detectaron problemas.") : ""
                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                visible: text !== ""
            }

            MichiButton {
                text: "Escanear biblioteca"
                variant: "primary"
                width: parent.width
                onClicked: {
                    if (root.doc && typeof root.doc.scan !== "undefined")
                        root.doc.scan()
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radiusMd; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: "Solo lectura — sin reparación automática"; kind: "info" }
                    StatusBadge { text: "Experimental"; kind: "experimental" }
                }
            }
        }
    }
}
