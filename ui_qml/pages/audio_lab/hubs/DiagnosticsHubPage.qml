import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

/**
 * Hub de Diagnóstico - Agrupa: Análisis, Integridad, Comparación A/B
 * Navegación interna desde AudioLabOverviewPage
 */
Page {
    id: page
    
    header: SectionHeader {
        text: "Diagnóstico"
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
            
            // Descripción del área
            Label {
                Layout.fillWidth: true
                text: "Herramientas para analizar características técnicas, verificar integridad de archivos y comparar versiones diferentes del mismo audio."
                font.pixelSize: 14
                color: MichiTheme.colors.textSecondary
                wrapMode: Text.Wrap
            }
            
            // Herramientas disponibles
            Repeater {
                model: [
                    { 
                        id: "analysis", 
                        text: "Análisis Técnico", 
                        icon: "📊", 
                        description: "Obtén información técnica detallada: códec, bitrate, sample rate, duración",
                        route: "audio_lab.analysis",
                        status: "available"
                    },
                    { 
                        id: "integrity", 
                        text: "Integridad de Archivos", 
                        icon: "✓", 
                        description: "Verifica que los archivos no estén corruptos o truncados",
                        route: "audio_lab.integrity",
                        status: "available"
                    },
                    { 
                        id: "comparison", 
                        text: "Comparación A/B", 
                        icon: "⚖️", 
                        description: "Compara dos versiones del mismo audio escuchando diferencias",
                        route: "audio_lab.comparison",
                        status: "available"
                    }
                ]
                
                delegate: GlassCard {
                    Layout.fillWidth: true
                    height: 100
                    
                    onClicked: {
                        // Navegar a la página específica
                        // En producción: pageStack.push(model.route)
                        console.log("Navegando a:", model.route)
                    }
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 15
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
                                    color: MichiTheme.colors.textPrimary
                                }
                                
                                Item { Layout.fillWidth: true }
                                
                                // Badge de estado
                                Rectangle {
                                    implicitWidth: statusLabel.implicitWidth + 10
                                    implicitHeight: 20
                                    radius: 4
                                    color: model.status === "available" ? MichiTheme.colors.success : 
                                           model.status === "experimental" ? MichiTheme.colors.accent : "#888888"
                                    
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
                                color: MichiTheme.colors.textSecondary
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                        
                        // Flecha de navegación
                        Label {
                            text: "›"
                            font.pixelSize: 28
                            color: MichiTheme.colors.accent
                        }
                    }
                }
            }
            
            // Información adicional
            GlassCard {
                Layout.fillWidth: true
                Layout.margins: 0
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label {
                        text: "💡 Consejo"
                        font.pixelSize: 14
                        font.bold: true
                        color: MichiTheme.colors.accent
                    }
                    
                    Label {
                        Layout.fillWidth: true
                        text: "Usa la comparación A/B para decidir qué versión de un archivo conservar antes de eliminar duplicados. El análisis técnico te ayudará a identificar archivos de baja calidad."
                        font.pixelSize: 13
                        color: MichiTheme.colors.textSecondary
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
