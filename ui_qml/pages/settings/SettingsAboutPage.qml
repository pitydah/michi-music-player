import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Settings About"
    focus: true
    id: root
    objectName: "settingsAboutPage"

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null

    property int pageState: AsyncStateView.READY
    property string errorMessage: ""
    property string errorDetails: ""
    property string appVersion: "1.0.0"
    property string osInfo: "Desconocido"
    property string pythonVersion: "Desconocido"
    property string qtVersion: "Desconocido"
    property string gstreamerVersion: "Desconocido"

    Accessible.role: Accessible.Pane
    Accessible.name: "Acerca de Michi Music Player"

    function refresh() {
        if (pageState === AsyncStateView.ERROR) return
        _loadSystemInfo()
    }

    function _loadSystemInfo() {
        if (!root.bridge) return
        root.appVersion = root.bridge.getValue("about/version") || "1.0.0"
        root.osInfo = root.bridge.getValue("about/os") || "Desconocido"
        root.pythonVersion = root.bridge.getValue("about/python_version") || "Desconocido"
        root.qtVersion = root.bridge.getValue("about/qt_version") || "Desconocido"
        root.gstreamerVersion = root.bridge.getValue("about/gstreamer_version") || "Desconocido"
    }

    function _checkForUpdates() {
        if (!root.bridge) return
        root.bridge.setValue("updates/check_now", true)
        if (root.notif) root.notif.showMessage("Buscando actualizaciones...", "info")
    }

    function _openUrl(url) {
        if (!root.bridge) return
        root.bridge.setValue("about/open_url", url)
    }

    Component.onCompleted: root.refresh()

    AsyncStateView {
        id: stateView
        anchors.fill: parent
        state: root.pageState
        title: root.pageState === AsyncStateView.ERROR ? "Error" : ""
        message: root.errorMessage
        details: root.errorDetails
        retryAvailable: root.pageState === AsyncStateView.ERROR
        onRetryRequested: { root.pageState = AsyncStateView.READY; root.refresh() }

        readyContent: ScrollView {
            id: scrollView
            anchors.fill: parent
            clip: true
            objectName: "settings.about.scrollView"
            Accessible.role: Accessible.ScrollArea
            Accessible.name: "Acerca de"

            ColumnLayout {
                width: Math.min(scrollView.width - MichiTheme.spacing.xl * 2, 800)
                anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                spacing: MichiTheme.spacing.lg
                
                

                PageHeader {
                    title: "Acerca de"
                    subtitle: "Información de Michi Music Player"
                }

                GlassCard {
                    id: appInfoCard
                    Layout.fillWidth: true
                    title: ""
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        Label {
                            text: "Michi Music Player"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.pageTitleSize
                            font.weight: MichiTheme.typography.weightBold
                        }

                        Label {
                            text: "Versión " + root.appVersion
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.cardTitleSize
                        }

                        Label {
                            text: "Reproductor de música premium para Linux/KDE con GStreamer, CoverFlow 3D y gestión avanzada de metadatos."
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            
                        }

                        Label {
                            text: "Stack: Python " + root.pythonVersion + " · PySide6 " + root.qtVersion + " · GStreamer " + root.gstreamerVersion
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                            
                        }

                        Label {
                            text: "Licencia: GPL-3.0-or-later (derivado de Miro Player)"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }

                        Label {
                            text: "Autor: Cristian · © 2026 Michi Music Player"
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.captionSize
                        }
                    }
                }

                GlassCard {
                    id: linksCard
                    Layout.fillWidth: true
                    title: "Enlaces"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            text: "Página principal"
                            variant: "ghost"
                            Layout.fillWidth: true
                            onClicked: root._openUrl("https://michi-music-player.org")
                            Accessible.name: "Página principal de Michi"
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "GitHub"
                            variant: "ghost"
                            Layout.fillWidth: true
                            onClicked: root._openUrl("https://github.com/pitydah/michi-music-player")
                            Accessible.name: "Repositorio de GitHub"
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Reportar un problema"
                            variant: "ghost"
                            Layout.fillWidth: true
                            onClicked: root._openUrl("https://github.com/pitydah/michi-music-player/issues")
                            Accessible.name: "Reportar un problema en GitHub"
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        MichiButton {
                            text: "Ver NOTICE (créditos)"
                            variant: "ghost"
                            Layout.fillWidth: true
                            onClicked: root._openUrl("https://github.com/pitydah/michi-music-player/blob/main/NOTICE")
                            Accessible.name: "Ver archivo NOTICE con créditos"
                        }
                    }
                }

                GlassCard {
                    id: updatesCard
                    Layout.fillWidth: true
                    title: "Actualizaciones"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.md

                        MichiButton {
                            text: "Buscar actualizaciones"
                            variant: "primary"
                            Layout.fillWidth: true
                            onClicked: root._checkForUpdates()
                            Accessible.name: "Buscar actualizaciones"
                        }
                    }
                }

                GlassCard {
                    id: systemInfoCard
                    Layout.fillWidth: true
                    title: "Información del sistema"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.sm

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.sm
                            Label {
                                text: "Sistema operativo"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.preferredWidth: 160
                            }
                            Label {
                                text: root.osInfo
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.sm
                            Label {
                                text: "Python"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.preferredWidth: 160
                            }
                            Label {
                                text: root.pythonVersion
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.sm
                            Label {
                                text: "Qt / PySide6"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.preferredWidth: 160
                            }
                            Label {
                                text: root.qtVersion
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: MichiTheme.colors.borderSubtle }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: MichiTheme.spacing.sm
                            Label {
                                text: "GStreamer"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.preferredWidth: 160
                            }
                            Label {
                                text: root.gstreamerVersion
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                GlassCard {
                    id: dependenciesCard
                    Layout.fillWidth: true
                    title: "Dependencias principales"
                    interactive: false

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.lg
                        spacing: MichiTheme.spacing.xs

                        Repeater {
                            model: [
                                "PySide6 — Qt 6 bindings para Python",
                                "GStreamer 1.28 — Motor de audio",
                                "SQLite 3 (WAL + FTS5) — Base de datos",
                                "mutagen — Lectura/escritura de metadatos",
                                "numpy + librosa — Análisis de audio",
                                "shazamio — Reconocimiento musical",
                                "PyAudio — Captura de audio en tiempo real",
                                "requests — Cliente HTTP"
                            ]

                            Label {
                                text: "• " + modelData
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.captionSize
                                
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    Keys.onEscapePressed: root.closeRequested()

    signal closeRequested()
}
