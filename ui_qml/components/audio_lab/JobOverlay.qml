import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../../theme"

/**
 * Overlay para monitoreo de trabajos en segundo plano
 * Cumple con especificación: panel global no intrusivo, progreso agregado, cancelación individual
 */
Rectangle {
    id: root
    
    anchors.fill: parent
    color: "#000000"
    opacity: active ? 0.7 : 0.0
    visible: opacity > 0
    z: 1000
    
    property bool active: false
    property var jobs: [] // [{id: "...", title: "...", progress: 0.5, status: "running"}]
    
    signal jobCancelled(string jobId)
    signal closeRequested()
    
    // Animación de fade in/out
    NumberAnimation {
        id: fadeAnim
        target: root
        property: "opacity"
        to: active ? 0.7 : 0.0
        duration: 300
        easing.type: Easing.OutCubic
    }
    
    onActiveChanged: fadeAnim.start()
    
    // Clickthrough - permite cerrar haciendo clic fuera
    MouseArea {
        anchors.fill: parent
        onClicked: {}
    }
    
    // Panel central
    GlassCard {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 500)
        height: Math.min(parent.height - 40, 400)
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 15
            
            // Encabezado
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                
                Label {
                    text: "Trabajos en Progreso"
                    font.pixelSize: 18
                    font.bold: true
                    color: MichiTheme.textPrimary
                }
                
                Item { Layout.fillWidth: true }
                
                // Botón cerrar
                Button {
                    text: "✕"
                    palette.buttonText: MichiTheme.textSecondary
                    palette.button: "transparent"
                    
                    onClicked: root.closeRequested()
                }
            }
            
            // Barra de progreso agregada (si hay múltiples trabajos)
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.jobs.length > 0
                spacing: 5
                
                RowLayout {
                    Layout.fillWidth: true
                    
                    Label {
                        text: `Progreso total: ${root.jobs.length} trabajo(s)`
                        font.pixelSize: 13
                        color: MichiTheme.textSecondary
                    }
                    
                    Item { Layout.fillWidth: true }
                    
                    Label {
                        text: `${Math.round(averageProgress * 100)}%`
                        font.pixelSize: 13
                        font.bold: true
                        color: MichiTheme.accent
                    }
                }
                
                ProgressBar {
                    Layout.fillWidth: true
                    value: averageProgress
                    indeterminate: averageProgress <= 0
                    
                    background: Rectangle {
                        implicitHeight: 6
                        radius: 3
                        color: "#2a2a2a"
                        
                        Rectangle {
                            width: parent.width * progressBar.value
                            height: parent.height
                            radius: 3
                            color: MichiTheme.accent
                        }
                    }
                }
            }
            
            // Separador
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 1
                color: MichiTheme.border
            }
            
            // Lista de trabajos individuales
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    
                    Repeater {
                        model: root.jobs
                        
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 70
                            radius: 8
                            color: "#1a1a1a"
                            
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12
                                
                                // Indicador de estado
                                Rectangle {
                                    implicitWidth: 32
                                    implicitHeight: 32
                                    radius: 16
                                    color: model.status === "running" ? MichiTheme.accent : 
                                           model.status === "completed" ? MichiTheme.success :
                                           model.status === "failed" ? MichiTheme.error : "#888888"
                                    
                                    Label {
                                        anchors.centerIn: parent
                                        text: model.status === "running" ? "⏳" : 
                                              model.status === "completed" ? "✓" : 
                                              model.status === "failed" ? "✕" : "?"
                                        font.pixelSize: 16
                                    }
                                }
                                
                                // Información del trabajo
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    
                                    Label {
                                        text: model.title || "Trabajo sin título"
                                        font.pixelSize: 13
                                        font.bold: true
                                        color: MichiTheme.textPrimary
                                        elide: Text.ElideRight
                                    }
                                    
                                    ProgressBar {
                                        Layout.fillWidth: true
                                        value: model.progress || 0
                                        implicitHeight: 4
                                        
                                        background: Rectangle {
                                            implicitHeight: 4
                                            radius: 2
                                            color: "#2a2a2a"
                                            
                                            Rectangle {
                                                width: parent.width * progressBar.value
                                                height: parent.height
                                                radius: 2
                                                color: MichiTheme.accent
                                            }
                                        }
                                    }
                                    
                                    Label {
                                        text: `${Math.round((model.progress || 0) * 100)}% completado`
                                        font.pixelSize: 11
                                        color: MichiTheme.textSecondary
                                    }
                                }
                                
                                // Botón cancelar (solo si está en ejecución)
                                Button {
                                    visible: model.status === "running"
                                    text: "Cancelar"
                                    palette.buttonText: MichiTheme.error
                                    palette.button: "transparent"
                                    
                                    onClicked: root.jobCancelled(model.id)
                                }
                            }
                        }
                    }
                    
                    // Estado vacío
                    Label {
                        visible: root.jobs.length === 0
                        text: "No hay trabajos activos"
                        font.pixelSize: 14
                        color: MichiTheme.textSecondary
                        horizontalAlignment: Text.AlignHCenter
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 40
                    }
                }
            }
        }
    }
    
    // Propiedad calculada para progreso promedio
    readonly property real averageProgress: {
        if (root.jobs.length === 0) return 0
        let total = 0
        for (let i = 0; i < root.jobs.length; i++) {
            total += (root.jobs[i].progress || 0)
        }
        return total / root.jobs.length
    }
}
