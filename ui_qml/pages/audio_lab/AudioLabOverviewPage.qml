import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../../ui_qml_bridge"

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
            title: "Audio Lab"
            subtitle: "Herramientas profesionales para analizar, identificar, preservar y configurar tu audio"
        }
        
        // Resumen de dependencias y trabajos
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            StatusBadge {
                status: overviewData && overviewData.dependencies && overviewData.dependencies.ffmpeg ? "success" : "warning"
                text: overviewData && overviewData.dependencies && overviewData.dependencies.ffmpeg ? "FFmpeg disponible" : "FFmpeg no disponible"
            }
            
            StatusBadge {
                status: overviewData && overviewData.dependencies && overviewData.dependencies.replaygain ? "success" : "warning"
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
        AreaCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            icon: overviewData && overviewData.areas && overviewData.areas.diagnostics 
                  ? overviewData.areas.diagnostics.icon : "🔍"
            title: overviewData && overviewData.areas && overviewData.areas.diagnostics 
                   ? overviewData.areas.diagnostics.title : "Diagnóstico"
            description: overviewData && overviewData.areas && overviewData.areas.diagnostics 
                         ? overviewData.areas.diagnostics.description : "Analiza, verifica integridad y compara archivos"
            status: overviewData && overviewData.areas && overviewData.areas.diagnostics 
                    ? overviewData.areas.diagnostics.status : "available"
            toolsCount: overviewData && overviewData.areas && overviewData.areas.diagnostics 
                        ? overviewData.areas.diagnostics.tools.length : 3
            
            onClicked: root.areaSelected("diagnostics")
        }
        
        // Tarjeta 2: Identificador de Audios
        AreaCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            icon: overviewData && overviewData.areas && overviewData.areas.identifier 
                  ? overviewData.areas.identifier.icon : "🆔"
            title: overviewData && overviewData.areas && overviewData.areas.identifier 
                   ? overviewData.areas.identifier.title : "Identificador de Audios"
            description: overviewData && overviewData.areas && overviewData.areas.identifier 
                         ? overviewData.areas.identifier.description : "Identifica, corrige metadatos y carátulas"
            status: overviewData && overviewData.areas && overviewData.areas.identifier 
                    ? overviewData.areas.identifier.status : "partial"
            toolsCount: overviewData && overviewData.areas && overviewData.areas.identifier 
                        ? overviewData.areas.identifier.tools.length : 4
            
            onClicked: root.areaSelected("identifier")
        }
        
        // Tarjeta 3: Respaldar
        AreaCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            icon: overviewData && overviewData.areas && overviewData.areas.backup 
                  ? overviewData.areas.backup.icon : "💾"
            title: overviewData && overviewData.areas && overviewData.areas.backup 
                   ? overviewData.areas.backup.title : "Respaldar"
            description: overviewData && overviewData.areas && overviewData.areas.backup 
                         ? overviewData.areas.backup.description : "Convierte, normaliza, ripea y organiza"
            status: overviewData && overviewData.areas && overviewData.areas.backup 
                    ? overviewData.areas.backup.status : "available"
            toolsCount: overviewData && overviewData.areas && overviewData.areas.backup 
                        ? overviewData.areas.backup.tools.length : 4
            
            onClicked: root.areaSelected("backup")
        }
        
        // Tarjeta 4: Perfiles de Salida
        AreaCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            icon: overviewData && overviewData.areas && overviewData.areas.output_profiles 
                  ? overviewData.areas.output_profiles.icon : "🎧"
            title: overviewData && overviewData.areas && overviewData.areas.output_profiles 
                   ? overviewData.areas.output_profiles.title : "Perfiles de Salida"
            description: overviewData && overviewData.areas && overviewData.areas.output_profiles 
                         ? overviewData.areas.output_profiles.description : "Configura DAC, EQ y reproducción"
            status: overviewData && overviewData.areas && overviewData.areas.output_profiles 
                    ? overviewData.areas.output_profiles.status : "available"
            toolsCount: overviewData && overviewData.areas && overviewData.areas.output_profiles 
                        ? overviewData.areas.output_profiles.tools.length : 3
            
            onClicked: root.areaSelected("output_profiles")
        }
        
        // Tarjeta 5: Inteligencia Local (ocupa toda la fila)
        AreaCard {
            Layout.fillWidth: true
            Layout.columnSpan: 2
            Layout.preferredHeight: 180
            icon: overviewData && overviewData.areas && overviewData.areas.local_intelligence 
                  ? overviewData.areas.local_intelligence.icon : "🧠"
            title: overviewData && overviewData.areas && overviewData.areas.local_intelligence 
                   ? overviewData.areas.local_intelligence.title : "Inteligencia Local"
            description: overviewData && overviewData.areas && overviewData.areas.local_intelligence 
                         ? overviewData.areas.local_intelligence.description : "Análisis acústico y automatización"
            status: overviewData && overviewData.areas && overviewData.areas.local_intelligence 
                    ? overviewData.areas.local_intelligence.status : "partial"
            toolsCount: overviewData && overviewData.areas && overviewData.areas.local_intelligence 
                        ? overviewData.areas.local_intelligence.tools.length : 4
            
            onClicked: root.areaSelected("local_intelligence")
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
        onRetry: {
            root.isLoading = true
            // Recargar datos
        }
    }
}
