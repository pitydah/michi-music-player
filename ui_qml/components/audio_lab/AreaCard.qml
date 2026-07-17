import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import MichiTheme

/**
 * Componente de tarjeta para áreas principales de Audio Lab
 * Cumple con especificación: 5 tarjetas principales con estado y herramientas
 */
GlassCard {
    id: root
    
    property string icon: "🔍"
    property string title: "Área"
    property string description: "Descripción del área"
    property string status: "available" // available, partial, experimental, missing_dependency
    property int toolsCount: 0
    
    signal clicked()
    
    hoverEnabled: true
    
    // Color según estado
    readonly property color statusColor: {
        switch(status) {
            case "available": return MichiTheme.success
            case "partial": return MichiTheme.warning
            case "experimental": return MichiTheme.accent
            case "missing_dependency": return MichiTheme.error
            default: return MichiTheme.textSecondary
        }
    }
    
    // Texto de estado legible
    readonly property string statusText: {
        switch(status) {
            case "available": return "Listo"
            case "partial": return "Parcial"
            case "experimental": return "Experimental"
            case "missing_dependency": return "Falta dependencia"
            default: return status
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        padding: 20
        spacing: 12
        
        // Icono y título
        RowLayout {
            Layout.fillWidth: true
            spacing: 15
            
            // Icono grande
            Label {
                text: root.icon
                font.pixelSize: 40
            }
            
            // Título y estado
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                
                Label {
                    text: root.title
                    font.pixelSize: 18
                    font.bold: true
                    color: MichiTheme.textPrimary
                    elide: Text.ElideRight
                }
                
                RowLayout {
                    spacing: 8
                    
                    // Badge de estado
                    Rectangle {
                        implicitWidth: statusLabel.implicitWidth + 12
                        implicitHeight: 20
                        radius: 4
                        color: root.statusColor
                        
                        Label {
                            id: statusLabel
                            anchors.centerIn: parent
                            text: root.statusText
                            font.pixelSize: 11
                            font.bold: true
                            color: "#ffffff"
                        }
                    }
                    
                    // Contador de herramientas
                    Label {
                        text: `${root.toolsCount} herramienta${root.toolsCount !== 1 ? 's' : ''}`
                        font.pixelSize: 12
                        color: MichiTheme.textSecondary
                    }
                }
            }
        }
        
        // Descripción
        Label {
            Layout.fillWidth: true
            text: root.description
            font.pixelSize: 13
            color: MichiTheme.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            maximumLineCount: 2
            elide: Text.ElideRight
        }
        
        // Espaciador flexible
        Item {
            Layout.fillHeight: true
        }
        
        // Indicador de clic (flecha)
        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 5
            
            Label {
                text: "Explorar"
                font.pixelSize: 12
                font.bold: true
                color: root.statusColor
            }
            
            Label {
                text: "›"
                font.pixelSize: 20
                color: root.statusColor
            }
        }
    }
    
    // Feedback visual al hacer hover
    states: State {
        name: "hovered"
        when: root.hovered
        PropertyChanges {
            target: root
            borderColor: root.statusColor
            borderWidth: 2
        }
    }
    
    transitions: Transition {
        PropertyAnimation {
            properties: "borderColor, borderWidth"
            duration: 200
            easing.type: Easing.OutCubic
        }
    }
}
