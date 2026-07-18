import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

/**
 * Diálogo de previsualización y confirmación para operaciones de Audio Lab
 * Cumple con especificación: vista previa de cambios, validación de espacio, confirmación explícita
 */
Dialog {
    id: root
    
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 40, 700)
    height: Math.min(parent.height - 40, 600)
    
    // Datos de entrada
    property var previewData: [] // [{original: "...", result: "...", size: "..."}]
    property bool spaceSufficient: true
    property string requiredSpace: "0 GB"
    property string availableSpace: "0 GB"
    property string operationTitle: "Confirmar Operación"
    property string operationDescription: ""
    
    // Señales de salida
    signal confirmed()
    signal cancelled()
    
    title: operationTitle
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 15
        
        // Descripción de la operación
        Label {
            Layout.fillWidth: true
            text: operationDescription
            font.pixelSize: 13
            color: MichiTheme.textSecondary
            wrapMode: Text.Wrap
            visible: operationDescription.length > 0
        }
        
        // Estado del espacio en disco
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Rectangle {
                implicitWidth: 32
                implicitHeight: 32
                radius: 16
                color: root.spaceSufficient ? MichiTheme.success : MichiTheme.error
                
                Label {
                    anchors.centerIn: parent
                    text: root.spaceSufficient ? "✓" : qsTr("⚠")
                    font.pixelSize: 18
                    color: "#ffffff"
                }
            }
            
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                
                Label {
                    text: root.spaceSufficient ? "Espacio suficiente" : qsTr("⚠ Espacio insuficiente")
                    font.pixelSize: 14
                    font.bold: true
                    color: root.spaceSufficient ? MichiTheme.success : MichiTheme.error
                }
                
                Label {
                    text: `Requerido: ${root.requiredSpace} | Disponible: ${root.availableSpace}`
                    font.pixelSize: 12
                    color: MichiTheme.textSecondary
                }
            }
        }
        
        // Separador
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: MichiTheme.border
        }
        
        // Título de vista previa
        Label {
            text: qsTr("Vista Previa de Cambios")
            font.pixelSize: 14
            font.bold: true
            color: MichiTheme.textPrimary
        }
        
        // Tabla de vista previa
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            TableView {
                id: previewTable
                width: parent.width
                clip: true
                
                model: root.previewData
                
                columnSpacing: 1
                rowSpacing: 1
                
                delegate: Rectangle {
                    color: index % 2 === 0 ? "#1a1a1a" : "#252525"
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 10
                        
                        // Archivo original
                        Label {
                            Layout.fillWidth: true
                            text: model.original || ""
                            font.pixelSize: 11
                            font.family: "Mono"
                            elide: Text.ElideMiddle
                            color: MichiTheme.textSecondary
                        }
                        
                        // Flecha
                        Label {
                            text: qsTr("→")
                            font.pixelSize: 16
                            color: MichiTheme.accent
                        }
                        
                        // Resultado propuesto
                        Label {
                            Layout.fillWidth: true
                            text: model.result || ""
                            font.pixelSize: 11
                            font.family: "Mono"
                            elide: Text.ElideMiddle
                            color: MichiTheme.success
                        }
                    }
                }
                
                // Encabezado inline (TableView.header no disponible en esta version)
                Item { height: 0; width: 1; visible: false }
            }
        }
        
        // Separador inferior
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 1
            color: MichiTheme.border
        }
        
        // Botones de acción
        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 12
            
            Button {
                text: qsTr("Cancelar")
                palette.buttonText: MichiTheme.textPrimary
                palette.button: "#3a3a3a"
                
                onClicked: {
                    root.cancelled()
                    root.close()
                }
            }
            
            Button {
                text: qsTr("Confirmar y Ejecutar")
                enabled: root.spaceSufficient
                highlighted: true
                
                palette.buttonText: root.spaceSufficient ? "#ffffff" : "#888888"
                palette.button: root.spaceSufficient ? MichiTheme.accent : "#3a3a3a"
                
                onClicked: {
                    root.confirmed()
                    root.close()
                }
            }
        }
    }
    
    // Overlay semitransparente
    background: Rectangle {
        color: "#000000"
        opacity: 0.5
    }
}
