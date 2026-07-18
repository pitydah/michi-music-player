import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme"
import "../components"
import "../components/foundations"
import "../components/states"
import "../components/layout"
import "../components/content"

Rectangle {
    Accessible.role: Accessible.Pane
    Accessible.name: "Component Gallery"
    objectName: "componentGallery"
    focus: true
    id: root

    property bool reducedMotion: false
    color: MichiTheme.colors.bgApp
    implicitWidth: 1280
    implicitHeight: 720

    MichiReducedMotion { id: motion; enabled: root.reducedMotion }
    MichiResponsive { id: responsive; availableWidth: root.width }

    Flickable {
        anchors.fill: parent
        contentHeight: gallery.implicitHeight + responsive.pageMargin * 2
        clip: true

        Column {
            id: gallery
            x: responsive.pageMargin
            y: responsive.pageMargin
            width: parent.width - responsive.pageMargin * 2
            spacing: MichiTheme.spacing.xl

            MichiPageHeader {
                width: parent.width
                title: qsTr("Michi UI Foundations")
                subtitle: qsTr("Galería aislada · ") + responsive.density + " · " + responsive.columnCount + " columnas"
            }

            MichiSection {
                title: qsTr("Controles")
                subtitle: qsTr("Normal, selected, disabled y focus-visible")

                Row {
                    spacing: MichiTheme.spacing.sm
                    MichiButton { text: qsTr("Primaria"); accessibleName: "Acción primaria" }
                    MichiButton { text: qsTr("Secundaria"); variant: "ghost" }
                    MichiButton { text: qsTr("Deshabilitada"); enabled: false }
                    MichiIconButton { iconSource: "../../icons/warm_play.svg"; tooltipText: "Reproducir"; selected: true }
                }
                MichiSearchField {
                    width: Math.min(parent.width, 420)
                    placeholderText: qsTr("Buscar solo en la galería")
                    accessibleName: "Buscar componentes"
                }
                MichiSlider { width: Math.min(parent.width, 420); value: 42; accessibleName: "Valor de ejemplo" }
                MichiProgressBar { width: Math.min(parent.width, 420); indeterminate: true; reducedMotion: root.reducedMotion }
            }

            StateGallery { width: parent.width }
            ResponsiveGallery { width: parent.width }
            TypographyGallery { width: parent.width }
        }
    }

    component StateGallery: MichiSection {
        title: qsTr("Estados canónicos")
        MichiResponsiveGrid {
            width: parent.width
            MichiLoadingState { message: qsTr("Operación asíncrona sin acceso a servicios"); reducedMotion: root.reducedMotion }
            MichiEmptyState { title: qsTr("Biblioteca vacía"); message: "Añade contenido cuando el workflow funcional esté disponible." }
            MichiErrorState { message: qsTr("Mensaje de error con detalles opcionales."); details: "Código público de ejemplo" }
            MichiUnavailableState { message: qsTr("Backend no disponible; la acción permanece visible.") }
        }
    }

    component ResponsiveGallery: MichiSection {
        title: qsTr("Contenido musical")
        subtitle: qsTr("Texto largo, sin portada y selección")
        MichiResponsiveGrid {
            width: parent.width
            MichiStatCard { label: qsTr("Canciones indexadas"); value: "12 480"; supportingText: "Densidad cómoda" }
            MichiAlbumTile { title: qsTr("Un título de álbum deliberadamente largo para validar elipsis"); artist: "Artista de ejemplo" }
            MichiArtistTile { title: qsTr("Artista sin imagen"); subtitle: "24 álbumes"; selected: true }
            MichiTrackRow { title: qsTr("Pista pública de ejemplo"); artist: "Michi"; album: "Galería"; duration: "4:12"; format: "FLAC"; current: true }
        }
    }

    component TypographyGallery: MichiSection {
        title: qsTr("Tipografía")
        Text { text: qsTr("Hero · ") + MichiTheme.typography.heroTitleSize; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.heroTitleSize }
        Text { text: qsTr("Título de página"); color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.pageTitleSize }
        Text { text: qsTr("Texto de cuerpo para lectura prolongada en escritorio."); color: MichiTheme.colors.textNormal; font.pixelSize: MichiTheme.typography.bodySize }
        Text { text: qsTr("Caption y metadatos secundarios"); color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }
    }
}
