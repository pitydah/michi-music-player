import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import MichiTheme
import "../../components"

/**
 * Hub de Perfiles de Salida - Configuración DAC, ReplayGain, Dispositivos
 */
Page {
    id: page
    
    header: SectionHeader {
        title: "Perfiles de Salida"
        subtitle: "Configura DAC, EQ y reproducción"
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
            
            Label {
                Layout.fillWidth: true
                text: "Configura cómo Michi entrega el audio a tus dispositivos: DACs, ecualización, ReplayGain y perfiles por dispositivo."
                font.pixelSize: 14
                color: MichiTheme.textSecondary
                wrapMode: Text.Wrap
            }
            
            Repeater {
                model: [
                    { 
                        id: "device_config", 
                        title: "Configuración de Dispositivo", 
                        icon: "🎧", 
                        description: "Selecciona dispositivo de salida, sample rate y bit depth",
                        route: "audio_lab.device_config",
                        status: "available"
                    },
                    { 
                        id: "replaygain", 
                        title: "ReplayGain", 
                        icon: "⚖️", 
                        description: "Configura normalización de volumen por pista o álbum",
                        route: "audio_lab.replaygain",
                        status: "available"
                    },
                    { 
                        id: "eq_dsp", 
                        title: "Ecualizador y DSP", 
                        icon: "🎚️", 
                        description: "Ajusta ecualización gráfica y efectos de procesamiento",
                        route: "audio_lab.eq",
                        status: "available"
                    }
                ]
                
                delegate: GlassCard {
                    Layout.fillWidth: true
                    height: 100
                    hoverEnabled: true
                    
                    RowLayout {
                        anchors.fill: parent
                        padding: 15
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
                                    color: MichiTheme.success
                                    Label {
                                        id: statusLabel
                                        anchors.centerIn: parent
                                        text: "Listo"
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
                padding: 15
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: "ℹ️ Nota"
                        font.pixelSize: 14
                        font.bold: true
                        color: MichiTheme.accent
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        text: "Los perfiles de salida afectan solo la reproducción en tiempo real. No modifican los archivos de audio originales."
                        font.pixelSize: 13
                        color: MichiTheme.textSecondary
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
