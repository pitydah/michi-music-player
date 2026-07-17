import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import MichiTheme
import "../../components"

/**
 * Hub de Respaldar - Agrupa: Conversión, Normalización, Ripeo CD, Grabación ADC, Organización
 * Navegación interna desde AudioLabOverviewPage
 */
Page {
    id: page
    
    header: SectionHeader {
        title: "Respaldar"
        subtitle: "Convierte, normaliza, ripea CDs y digitaliza vinilos"
        onBackClicked: pageStack.pop()
    }
    
    ScrollView {
        anchors.fill: parent
        contentWidth: container.width
        clip: true
        
        ColumnLayout {
            id: container
            width: Math.max(parent.width, 800)
            padding: 20
            spacing: 20
            
            // Descripción del área
            Label {
                Layout.fillWidth: true
                text: "Herramientas para preservar tu colección musical: convierte formatos, normaliza volumen, extrae CDs de audio y digitaliza vinilos o cassettes."
                font.pixelSize: 14
                color: MichiTheme.textSecondary
                wrapMode: Text.Wrap
            }
            
            // Herramientas disponibles
            Repeater {
                model: [
                    { 
                        id: "conversion", 
                        title: "Conversión de Formatos", 
                        icon: "🔄", 
                        description: "Convierte entre FLAC, MP3, AAC, Opus, WAV preservando metadatos",
                        route: "audio_lab.conversion",
                        status: "available"
                    },
                    { 
                        id: "normalization", 
                        title: "Normalización", 
                        icon: "⚖️", 
                        description: "Ajusta el volumen usando ReplayGain (no destructivo) o normalización destructiva",
                        route: "audio_lab.normalization",
                        status: "available"
                    },
                    { 
                        id: "cd_ripping", 
                        title: "Ripeo de CD", 
                        icon: "💿", 
                        description: "Extrae pistas de CDs de audio con verificación de seguridad",
                        route: "audio_lab.cd_rip",
                        status: "experimental"
                    },
                    { 
                        id: "adc_recording", 
                        title: "Grabación ADC (Vinilo/Cassette)", 
                        icon: "🎙️", 
                        description: "Digitaliza vinilos y cassettes desde tocadiscos USB con ecualización RIAA",
                        route: "audio_lab.adc_record",
                        status: "experimental"
                    },
                    { 
                        id: "organization", 
                        title: "Organización de Archivos", 
                        icon: "📂", 
                        description: "Reorganiza tu biblioteca con estructuras de carpetas personalizadas",
                        route: "audio_lab.organize",
                        status: "available"
                    }
                ]
                
                delegate: GlassCard {
                    Layout.fillWidth: true
                    height: 100
                    hoverEnabled: true
                    
                    onClicked: {
                        console.log("Navegando a:", model.route)
                        // En producción: pageStack.push(model.route)
                    }
                    
                    RowLayout {
                        anchors.fill: parent
                        padding: 15
                        spacing: 20
                        
                        // Icono
                        Label {
                            text: model.icon
                            font.pixelSize: 36
                        }
                        
                        // Información
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
                                
                                // Badge de estado
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
                                elide: Text.ElideRight
                            }
                        }
                        
                        // Flecha de navegación
                        Label {
                            text: "›"
                            font.pixelSize: 28
                            color: MichiTheme.accent
                        }
                    }
                }
            }
            
            // Información adicional
            GlassCard {
                Layout.fillWidth: true
                padding: 15
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: "⚠️ Importante"
                        font.pixelSize: 14
                        font.bold: true
                        color: MichiTheme.warning
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        text: "Las operaciones de conversión y normalización destructiva crean copias nuevas. Los archivos originales nunca se modifican ni eliminan automáticamente. Siempre verifica el espacio en disco antes de comenzar."
                        font.pixelSize: 13
                        color: MichiTheme.textSecondary
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
