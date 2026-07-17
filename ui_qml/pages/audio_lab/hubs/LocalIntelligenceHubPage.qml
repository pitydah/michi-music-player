import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

/**
 * Hub de Inteligencia Local - Similitud acústica, Radio local, Smart Mix
 */
Page {
    id: page
    
    header: SectionHeader {
        text: "Inteligencia Local"
    }
    
    ScrollView {
        anchors.fill: parent
        contentWidth: container.width
        clip: true
        
        ColumnLayout {
            id: container
            width: Math.max(parent.width, 800)
            anchors.margins: 20
            spacing: 20
            
            Label {
                Layout.fillWidth: true
                text: "Características avanzadas que analizan tu biblioteca para encontrar canciones similares, generar radios locales y crear mixes inteligentes."
                font.pixelSize: 14
                color: MichiTheme.textSecondary
                wrapMode: Text.Wrap
            }
            
            Repeater {
                model: [
                    { 
                        id: "acoustic_features", 
                        text: "Características Acústicas", 
                        icon: "📈", 
                        description: "Analiza BPM, tonalidad, energía y otras características",
                        route: "audio_lab.acoustic_features",
                        status: "experimental"
                    },
                    { 
                        id: "similar_songs", 
                        text: "Canciones Similares", 
                        icon: "🎯", 
                        description: "Encuentra canciones similares basadas en características acústicas",
                        route: "audio_lab.similar_songs",
                        status: "experimental"
                    },
                    { 
                        id: "local_radio", 
                        text: "Radio Local", 
                        icon: "📻", 
                        description: "Genera una cola dinámica desde tu colección local",
                        route: "audio_lab.local_radio",
                        status: "available"
                    },
                    { 
                        id: "smart_mix", 
                        text: "Smart Mix", 
                        icon: "🎵", 
                        description: "Crea mezclas automáticas basadas en preferencias y contexto",
                        route: "mix.hub",
                        status: "available"
                    }
                ]
                
                delegate: GlassCard {
                    Layout.fillWidth: true
                    height: 100
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 20
                        
                        Label { text: model.icon; font.pixelSize: 36 }
                        
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: model.title
                                    font.pixelSize: 16
                                    font.bold: true
                                    color: MichiTheme.textPrimary
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: statusLabel.implicitWidth + 10
                                    implicitHeight: 20
                                    radius: 4
                                    color: model.status === "available" ? MichiTheme.success : 
                                           model.status === "experimental" ? MichiTheme.accent : "#888888"
                                    Label {
                                        id: statusLabel
                                        anchors.centerIn: parent
                                        text: model.status === "available" ? "Listo" : 
                                              model.status === "experimental" ? "Experimental" : "Parcial"
                                        font.pixelSize: 11
                                        font.bold: true
                                        color: "#ffffff"
                                    }
                                }
                            }
                            
                            Label {
                                Layout.fillWidth: true
                                text: model.description
                                font.pixelSize: 13
                                color: MichiTheme.textSecondary
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                            }
                        }
                        
                        Label { text: "›"; font.pixelSize: 28; color: MichiTheme.accent }
                    }
                }
            }
            
            GlassCard {
                Layout.fillWidth: true
                anchors.margins: 15
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: "⚠️ Experimental"
                        font.pixelSize: 14
                        font.bold: true
                        color: MichiTheme.accent
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        text: "Las funciones de análisis acústico requieren librerías adicionales (librosa). Algunos resultados pueden variar según la calidad del análisis."
                        font.pixelSize: 13
                        color: MichiTheme.textSecondary
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
