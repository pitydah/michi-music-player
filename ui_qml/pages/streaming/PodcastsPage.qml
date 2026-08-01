import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../materials"
import "../../components"

/* Podcasts — conceptual premium page for a planned feature.
 * Shows the product vision only: there is no subscription manager,
 * no downloads and no episodes in this installation.
 */
PlannedFeaturePage {
    id: root
    objectName: "podcastsPage"

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Podcasts")

    featureTitle: qsTr("Podcasts")
    featureDescription: qsTr("Tus podcasts dentro de Michi: suscripciones por RSS, episodios nuevos al entrar, reanudación exacta donde lo dejaste y descargas para escuchar sin conexión. Audio primero, sin vídeo.")
    featureIcon: "podcasts"
    featureState: "planned"
    statusLabel: qsTr("Planificado")
    statusKind: "info"
    primaryActionText: qsTr("Volver a Streaming")
    secondaryActionText: qsTr("Explorar Radio")

    onPrimaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("streaming")
    }
    onSecondaryActionRequested: {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigate("streaming.radio")
    }

    component VisionCard: GlassMaterial {
        property string cardIcon: "podcasts"
        property string cardTitle: ""
        property string cardText: ""

        width: root.contentWidth
        height: cardLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "status"
        radius: MichiTheme.radius.md

        RowLayout {
            id: cardLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            MichiIcon {
                Layout.alignment: Qt.AlignTop
                iconKey: cardIcon
                size: MichiTheme.iconSizeLarge
                color: MichiTheme.colors.accentPrimary
                accessibleName: cardTitle
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: MichiTheme.spacing.xs

                Text {
                    Layout.fillWidth: true
                    text: cardTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.cardTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    text: cardText
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.secondarySize
                    wrapMode: Text.WordWrap
                    lineHeight: MichiTheme.typography.lineHeightBody
                }
            }
        }
    }

    SectionHeader { text: qsTr("Lo que podrás hacer") }

    VisionCard {
        cardIcon: "podcasts"
        cardTitle: qsTr("Suscripciones por RSS")
        cardText: qsTr("Añade programas pegando su feed RSS o buscando por nombre. Michi comprobará episodios nuevos automáticamente.")
    }

    VisionCard {
        cardIcon: "streaming"
        cardTitle: qsTr("Episodios nuevos y continuar escuchando")
        cardText: qsTr("Una bandeja de episodios recientes y la reanudación exacta de cada episodio empezado, con progreso por programa.")
    }

    VisionCard {
        cardIcon: "sync"
        cardTitle: qsTr("Descargas sin conexión")
        cardText: qsTr("Descarga episodios para escucharlos sin red y sincroniza el progreso con tus dispositivos cuando la sincronización esté disponible.")
    }

    GlassMaterial {
        width: root.contentWidth
        height: noteLayout.implicitHeight + MichiTheme.spacing.lg * 2
        variant: "accent"
        radius: MichiTheme.radius.md

        ColumnLayout {
            id: noteLayout
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.xs

            Text {
                Layout.fillWidth: true
                text: qsTr("Estado real de esta instalación")
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.cardTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("El gestor de suscripciones y descargas todavía no está implementado. No hay programas, episodios ni descargas que mostrar: todo lo anterior es la visión de producto, no funcionalidad activa.")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.secondarySize
                wrapMode: Text.WordWrap
                lineHeight: MichiTheme.typography.lineHeightBody
            }
        }
    }
}
