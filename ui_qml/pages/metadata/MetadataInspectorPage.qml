import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var md: typeof metadataBridge !== "undefined" ? metadataBridge : null

    function inspect(filepath) {
        if (root.md && typeof root.md.inspectTrack !== "undefined") {
            root.md.inspectTrack(filepath)
        }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            Text {
                text: "Inspector de metadatos"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.pageTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Loader {
                width: parent.width
                sourceComponent: root.md && root.md.hasSelection ? inspectorContent : emptyComponent
            }
        }
    }

    Component {
        id: emptyComponent
        Column {
            width: 360
            spacing: MichiTheme.spacing.lg
            anchors.centerIn: parent

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 48; height: 48; radius: MichiTheme.radiusMd
                color: MichiTheme.colors.accentSurface
                Text {
                    anchors.centerIn: parent
                    text: "MI"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold
                    font.letterSpacing: 1.5; opacity: 0.70
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Selecciona una canción"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightMedium
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Selecciona una canción en la Biblioteca para inspeccionar sus metadatos."
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Component {
        id: inspectorContent
        Column {
            width: parent.width
            spacing: MichiTheme.spacing.lg

            GlassMaterial {
                width: parent.width
                height: 120
                radius: MichiTheme.radiusMd
                variant: "base"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.sm

                    Text {
                        text: root.md ? root.md.trackTitle : "—"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: root.md ? root.md.trackArtist : ""
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        visible: text !== ""
                    }

                    Text {
                        text: root.md ? root.md.trackAlbum : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: text !== ""
                    }
                }
            }

            GlassMaterial {
                width: parent.width
                radius: MichiTheme.radiusMd
                variant: "base"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Metadatos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                        bottomPadding: MichiTheme.spacing.sm
                    }

                    Repeater {
                        model: root.md ? root.md.fields : []

                        MetadataFieldRow {
                            width: parent.width
                            fieldLabel: modelData.label || ""
                            fieldValue: modelData.value || ""
                        }
                    }
                }
            }

            MetadataArtworkPreview {
                width: parent.width
                artworkStatus: root.md ? root.md.artworkStatus : ""
                coverKey: root.md && root.md.hasSelection ? "inspector" : ""
            }

            GlassMaterial {
                width: parent.width
                radius: MichiTheme.radiusMd
                variant: "base"

                Column {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.lg
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Acciones"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.cardTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    MichiButton {
                        text: "Previsualizar sugerencias"
                        variant: "secondary"
                        onClicked: {
                            if (root.md && typeof root.md.previewSuggestedFixes !== "undefined") {
                                root.md.previewSuggestedFixes()
                            }
                        }
                    }

                    MichiButton {
                        text: "Aplicar cambios"
                        variant: "ghost"
                        enabled: root.md ? root.md.canApply : false
                        tooltip: "La escritura de metadatos se habilitará en una fase posterior."
                    }
                }
            }
        }
    }
}
