import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab"
    objectName: "audioLabPage"
    focus: true
    id: root

    property string pageState: "LOADING"
    property var alab: typeof audioLabBridge !== "undefined" ? audioLabBridge : null

    Component.onCompleted: {
        root.pageState = "READY"
        if (root.alab && typeof root.alab.refresh !== "undefined")
            root.alab.refresh()
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

            HeroMaterial {
                width: parent.width; height: 140; radius: MichiTheme.radius.lg; showGlow: true
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.xl; spacing: MichiTheme.spacing.sm
                    Text {
                        text: qsTr("Audio Lab")
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold
                    }
                    Text {
                        text: qsTr("Herramientas de análisis, conversión y diagnóstico para tu biblioteca musical.")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize; width: parent.width * 0.70; wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                width: parent.width; height: 80
                title: qsTr("Inspector de metadatos")
                subtitle: qsTr("Revisa campos, carátulas y consistencia de una pista.")
                variant: "primary"
                onClicked: {
                    if (typeof navigationBridge !== "undefined" && navigationBridge)
                        navigationBridge.navigate("metadata_inspector")
                }
            }

            SectionHeader { text: qsTr("Estado de la biblioteca"); width: parent.width }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "base"
                Row {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.xl
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.totalTracks : qsTr("—"); color: MichiTheme.colors.accentBlue; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: qsTr("Canciones"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.missingMetadata : qsTr("—"); color: root.alab && root.alab.missingMetadata > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: qsTr("Sin metadata"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                    Column { spacing: MichiTheme.spacing.xs
                        Text { text: root.alab ? root.alab.missingCovers : qsTr("—"); color: root.alab && root.alab.missingCovers > 0 ? MichiTheme.colors.warning : MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize; font.weight: MichiTheme.typography.weightBold }
                        Text { text: qsTr("Sin carátula"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize }
                    }
                }
            }

            SectionHeader { text: qsTr("Herramientas"); width: parent.width }

            Grid {
                width: parent.width; columns: 2; columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                Repeater {
                    model: root.alab ? root.alab.modules : []

                    GlassCard {
                        width: (parent.width - MichiTheme.spacing.md) / 2; height: 90
                        title: modelData.title || ""
                        subtitle: modelData.desc || ""
                        variant: modelData.status === "available" ? "base" : "status"
                        onClicked: {
                            if (modelData.id === "diagnostics" && typeof navigationBridge !== "undefined")
                                navigationBridge.navigate("audio_lab")
                        }
                    }
                }
            }

            SectionHeader { text: qsTr("Herramientas QML"); width: parent.width }

            Grid {
                width: parent.width; columns: 2; columnSpacing: MichiTheme.spacing.md; rowSpacing: MichiTheme.spacing.md

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                    title: qsTr("Smart Tagging"); subtitle: "Sugerencias de metadatos"
                    variant: "primary"
                    onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("smart_tagging") }
                    StatusBadge { anchors.top: parent.top; anchors.right: parent.right; anchors.margins: MichiTheme.spacing.sm; text: qsTr("Funcional"); kind: "success" }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                    title: qsTr("Ecualizador"); subtitle: "Ajuste de frecuencias"
                    variant: "base"
                    onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("eq") }
                    StatusBadge { anchors.top: parent.top; anchors.right: parent.right; anchors.margins: MichiTheme.spacing.sm; text: qsTr("Funcional"); kind: "success" }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                    title: qsTr("Library Doctor"); subtitle: "Diagnóstico de biblioteca"
                    variant: "base"
                    onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("library_doctor") }
                    StatusBadge { anchors.top: parent.top; anchors.right: parent.right; anchors.margins: MichiTheme.spacing.sm; text: qsTr("Funcional"); kind: "success" }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                    title: qsTr("Disc Lab"); subtitle: "Laboratorio de discos"
                    variant: "base"
                    onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("disc_lab") }
                    StatusBadge { anchors.top: parent.top; anchors.right: parent.right; anchors.margins: MichiTheme.spacing.sm; text: qsTr("Experimental"); kind: "experimental" }
                }

                GlassCard {
                    width: (parent.width - MichiTheme.spacing.md) / 2; height: 80
                    title: qsTr("Inspector metadata"); subtitle: "Edición de campos"
                    variant: "primary"
                    onClicked: { if (typeof navigationBridge !== "undefined") navigationBridge.navigate("metadata_inspector") }
                    StatusBadge { anchors.top: parent.top; anchors.right: parent.right; anchors.margins: MichiTheme.spacing.sm; text: qsTr("Funcional"); kind: "success" }
                }
            }

            GlassMaterial {
                width: parent.width; radius: MichiTheme.radius.md; variant: "status"
                Column {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.lg; spacing: MichiTheme.spacing.sm
                    StatusBadge { text: qsTr("Solo lectura"); kind: "info" }
                    StatusBadge { text: qsTr("Interfaz clásica disponible"); kind: "disconnected" }
                }
            }
        }
    }
}
