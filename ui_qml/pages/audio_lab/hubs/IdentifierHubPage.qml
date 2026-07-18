import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

/**
 * Hub de Identificador - Agrupa: Fingerprint, Metadatos, Carátulas, Letras
 */
Page {
    id: page
    
    header: SectionHeader {
        text: qsTr("Identificador de Audios")
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
                text: qsTr("Herramientas para identificar canciones desconocidas, corregir metadatos incorrectos y agregar carátulas y letras faltantes.")
                font.pixelSize: 14
                color: MichiTheme.colors.textSecondary
                wrapMode: Text.Wrap
            }
            
            Repeater {
                model: [
                    { 
                        id: "fingerprint", 
                        text: qsTr("Fingerprint Acústico"), 
                        icon: "🆔", 
                        description: "Identifica canciones usando huella acústica (AcoustID)",
                        route: "audio_lab.fingerprint",
                        status: "partial"
                    },
                    { 
                        id: "metadata", 
                        text: qsTr("Editor de Metadatos"), 
                        icon: "📝", 
                        description: "Edita tags ID3: título, artista, álbum, género, año",
                        route: "audio_lab.metadata",
                        status: "available"
                    },
                    { 
                        id: "covers", 
                        text: qsTr("Carátulas"), 
                        icon: "🖼️", 
                        description: "Busca y agrega carátulas desde MusicBrainz y otras fuentes",
                        route: "audio_lab.covers",
                        status: "available"
                    },
                    { 
                        id: "lyrics", 
                        text: qsTr("Letras"), 
                        icon: "🎵", 
                        description: "Busca y sincroniza letras de canciones",
                        route: "audio_lab.lyrics",
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
                                    color: model.status === "available" ? MichiTheme.colors.success : "#888888"
                                    Label {
                                        id: statusLabel
                                        anchors.centerIn: parent
                                        text: model.status === "available" ? "Listo" : qsTr("Parcial")
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
                        
                        Label { text: qsTr("›"); font.pixelSize: 28;                 color: MichiTheme.colors.accent }
                    }
                }
            }
        }
    }
}
