import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: typeof historyBridge !== "undefined" ? historyBridge : null
    property string _state: "LOADING"
    property var _stats: ({})

    objectName: "history.statisticsPage"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Estadísticas de historial"
    Accessible.description: "Panel de estadísticas del historial de reproducción"

    function loadStats() {
        root._state = "LOADING"
        if (root.bridge && typeof root.bridge.getStatistics !== "undefined") {
            var result = root.bridge.getStatistics()
            if (result && result.ok) {
                root._stats = result
                root._state = "READY"
            } else {
                root._state = "EMPTY"
            }
        } else {
            root._state = "EMPTY"
        }
    }

    Component.onCompleted: root.loadStats()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        spacing: MichiTheme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            objectName: "history.statsHeader"

            Label {
                text: "Estadísticas"
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                color: MichiTheme.colors.textPrimary
                font.weight: MichiTheme.typography.weightSemiBold
                Accessible.role: Accessible.Heading
                Accessible.name: "Estadísticas del historial"
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: "Actualizar"
                variant: "ghost"
                onClicked: root.loadStats()
                objectName: "history.statsRefresh"
                Accessible.name: "Actualizar estadísticas"
            }
        }

        LoadingState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._state === "LOADING"
            title: "Cargando estadísticas"
            objectName: "history.statsLoading"
        }

        EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._state === "EMPTY"
            title: "Sin datos estadísticos"
            subtitle: "No hay suficientes datos de reproducción para generar estadísticas."
            iconText: "\uD83D\uDCCA"
            objectName: "history.statsEmpty"
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._state === "READY"
            objectName: "history.statsContent"
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: MichiTheme.spacing.lg

                RowLayout {
                    Layout.fillWidth: true
                    spacing: MichiTheme.spacing.md

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        title: (root._stats.total_plays || 0).toString()
                        subtitle: "Reproducciones totales"
                        objectName: "history.stat.totalPlays"
                    }
                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        title: (root._stats.unique_tracks || 0).toString()
                        subtitle: "Pistas únicas"
                        objectName: "history.stat.uniqueTracks"
                    }
                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        title: (root._stats.unique_artists || 0).toString()
                        subtitle: "Artistas"
                        objectName: "history.stat.uniqueArtists"
                    }
                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        title: (root._stats.listening_time_hours || 0) + "h"
                        subtitle: "Tiempo escuchado"
                        objectName: "history.stat.listeningTime"
                    }
                }

                SectionHeader {
                    text: "Top canciones"
                    width: parent.width
                    objectName: "history.section.topTracks"
                    Accessible.name: "Canciones más reproducidas"
                }

                Repeater {
                    model: root._stats.top_tracks || []
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 24
                        }
                        CoverImage {
                            width: 32; height: 32
                            coverKey: modelData.album_key || ""
                            coverRadius: MichiTheme.radiusXs
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.title || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: (modelData.artist || "") + " · " + (modelData.play_count || 0) + " plays"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                SectionHeader {
                    text: "Top álbumes"
                    width: parent.width
                    objectName: "history.section.topAlbums"
                    Accessible.name: "Álbumes más reproducidos"
                }

                Repeater {
                    model: root._stats.top_albums || []
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 24
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.album || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: (modelData.artist || "") + " · " + (modelData.play_count || 0) + " plays"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                SectionHeader {
                    text: "Top artistas"
                    width: parent.width
                    objectName: "history.section.topArtists"
                    Accessible.name: "Artistas más reproducidos"
                }

                Repeater {
                    model: root._stats.top_artists || []
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: (index + 1) + "."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 24
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                text: modelData.artist || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: (modelData.play_count || 0) + " plays"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.metaSize
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                SectionHeader {
                    text: "Géneros"
                    width: parent.width
                    objectName: "history.section.genres"
                    Accessible.name: "Desglose por género"
                }

                Repeater {
                    model: root._stats.genre_breakdown || []
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: modelData.genre || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }
                        MichiProgressBar {
                            Layout.preferredWidth: 120
                            value: modelData.percentage || 0
                            from: 0; to: 100
                            accessibleName: modelData.genre + ": " + modelData.percentage + "%"
                        }
                        Text {
                            text: (modelData.percentage || 0) + "%"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            width: 40
                            horizontalAlignment: Text.AlignRight
                        }
                    }
                }

                Item { Layout.preferredHeight: MichiTheme.spacing.xl }
            }
        }
    }
}
