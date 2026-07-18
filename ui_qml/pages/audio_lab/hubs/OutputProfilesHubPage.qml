import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

/**
 * Hub de Perfiles de Salida - Configuración DAC, ReplayGain, Dispositivos
 */
Page {
    id: page
    
    header: SectionHeader {
        text: qsTr("Perfiles de Salida")
    }
    
    ScrollView {
        anchors.fill: parent
        contentWidth: container.width
        clip: true
        
        ColumnLayout {
            id: container
            Layout.fillWidth: true
            Layout.minimumWidth: 800
            spacing: 20
            
            Label {
                Layout.fillWidth: true
                text: qsTr("Configura cómo Michi entrega el audio a tus dispositivos: DACs, ecualización, ReplayGain y perfiles por dispositivo.")
                font.pixelSize: 14
                color: MichiTheme.colors.textSecondary
                wrapMode: Text.Wrap
            }
            
            Repeater {
                model: [
                    { 
                        id: "device_config", 
                        text: qsTr("Configuración de Dispositivo"), 
                        icon: "🎧", 
                        description: "Selecciona dispositivo de salida, sample rate y bit depth",
                        route: "audio_lab.device_config",
                        status: "available"
                    },
                    { 
                        id: "replaygain", 
                        text: qsTr("ReplayGain"), 
                        icon: "⚖️", 
                        description: "Configura normalización de volumen por pista o álbum",
                        route: "audio_lab.replaygain",
                        status: "available"
                    },
                    { 
                        id: "eq_dsp", 
                        text: qsTr("Ecualizador y DSP"), 
                        icon: "🎚️", 
                        description: "Ajusta ecualización gráfica y efectos de procesamiento",
                        route: "audio_lab.eq",
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
                                    color: MichiTheme.colors.textPrimary
                                }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    implicitWidth: statusLabel.implicitWidth + 10
                                    implicitHeight: 20
                                    radius: 4
                                    color: MichiTheme.colors.success
                                    Label {
                                        id: statusLabel
                                        anchors.centerIn: parent
                                        text: qsTr("Listo")
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
                                color: MichiTheme.colors.textSecondary
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                            }
                        }
                        
                        Label { text: qsTr("›"); font.pixelSize: 28; color: MichiTheme.colors.accent }
                    }
                }
            }
            
            GlassCard {
                Layout.fillWidth: true
                Layout.margins: 0
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: qsTr("ℹ️ Nota")
                        font.pixelSize: 14
                        font.bold: true
                        color: MichiTheme.colors.accent
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Los perfiles de salida afectan solo la reproducción en tiempo real. No modifican los archivos de audio originales.")
                        font.pixelSize: 13
                        color: MichiTheme.colors.textSecondary
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
