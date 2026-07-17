import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../components"

GlassCard {
    id: root
    
    signal areaSelected(string areaKey)
    
    property var overviewData: null
    property bool isLoading: false
    
    // Header
    ColumnLayout {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 20
        spacing: 12
        
        SectionHeader {
            Layout.fillWidth: true
            text: "Audio Lab"

        }
        
        // Resumen de dependencias y trabajos
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            StatusBadge {
                kind: overviewData && overviewData.dependencies && overviewData.dependencies.ffmpeg ? "success" : "warning"
                text: overviewData && overviewData.dependencies && overviewData.dependencies.ffmpeg ? "FFmpeg disponible" : "FFmpeg no disponible"
            }
            
            StatusBadge {
                kind: overviewData && overviewData.dependencies && overviewData.dependencies.replaygain ? "success" : "warning"
                text: overviewData && overviewData.dependencies && overviewData.dependencies.replaygain ? "ReplayGain disponible" : "ReplayGain no disponible"
            }
            
            Item { Layout.fillWidth: true }
            
            Label {
                text: overviewData && overviewData.active_jobs > 0 
                    ? `${overviewData.active_jobs} trabajo(s) activo(s)` 
                    : "Sin trabajos activos"
                font.pixelSize: 12
                color: MichiTheme.textSecondary
            }
        }
    }
    
    // Grid de 5 tarjetas principales
    GridLayout {
        anchors.top: parent.top
        anchors.topMargin: 140
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        columns: 2
        rowSpacing: 16
        columnSpacing: 16
        
        // Tarjeta 1: Diagnóstico
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 180
            radius: MichiTheme.radius.md
            color: ma1.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
            border.width: 1; border.color: MichiTheme.colors.borderCard
            ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { text: "🔍"; font.pixelSize: 28 }
                Text { text: "Diagnóstico"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                Text { text: "Analiza, verifica integridad y compara archivos"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            }
            MouseArea { id: ma1; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("diagnostics") }
        }
        
        // Tarjeta 2: Identificador de Audios
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 180
            radius: MichiTheme.radius.md
            color: ma2.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
            border.width: 1; border.color: MichiTheme.colors.borderCard
            ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { text: "🆔"; font.pixelSize: 28 }
                Text { text: "Identificador de Audios"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                Text { text: "Identifica, corrige metadatos y carátulas"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            }
            MouseArea { id: ma2; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("identifier") }
        }
        
        // Tarjeta 3: Respaldar
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 180
            radius: MichiTheme.radius.md
            color: ma3.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
            border.width: 1; border.color: MichiTheme.colors.borderCard
            ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { text: "💾"; font.pixelSize: 28 }
                Text { text: "Respaldar"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                Text { text: "Convierte, normaliza, ripea y organiza"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            }
            MouseArea { id: ma3; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("backup") }
        }
        
        // Tarjeta 4: Perfiles de Salida
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 180
            radius: MichiTheme.radius.md
            color: ma4.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
            border.width: 1; border.color: MichiTheme.colors.borderCard
            ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { text: "🎧"; font.pixelSize: 28 }
                Text { text: "Perfiles de Salida"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                Text { text: "Configura DAC, EQ y reproducción"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            }
            MouseArea { id: ma4; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("output_profiles") }
        }
        
        // Tarjeta 5: Inteligencia Local (ocupa toda la fila)
        Rectangle {
            Layout.fillWidth: true; Layout.columnSpan: 2; Layout.preferredHeight: 180
            radius: MichiTheme.radius.md
            color: ma5.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
            border.width: 1; border.color: MichiTheme.colors.borderCard
            ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                Text { text: "🧠"; font.pixelSize: 28 }
                Text { text: "Inteligencia Local"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                Text { text: "Análisis acústico y automatización"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
            }
            MouseArea { id: ma5; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("local_intelligence") }
        }
    }
    
    // Estado de carga
    LoadingState {
        visible: root.isLoading
        anchors.fill: parent
        message: "Cargando Audio Lab..."
    }
    
    // Estado de error
    ErrorState {
        visible: !root.isLoading && overviewData === null
        anchors.fill: parent
        message: "No se pudieron cargar los datos de Audio Lab"
        onRetryRequested: {
            root.isLoading = true
        }
    }
}
