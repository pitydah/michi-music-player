import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property string state: "READY"

    objectName: "settings.about"
    Accessible.role: Accessible.Panel
    Accessible.name: "Acerca de"
    Accessible.description: "Información de la aplicación, licencia y créditos"

    signal closeRequested()
    signal checkUpdates()

    states: [
        State { name: "LOADING"; PropertyChanges { target: loader; sourceComponent: loadingComp } },
        State { name: "READY"; PropertyChanges { target: loader; sourceComponent: readyComp } },
        State { name: "ERROR"; PropertyChanges { target: loader; sourceComponent: errorComp } }
    ]
    state: "READY"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true

        Keys.onEscapePressed: root.closeRequested()

        Loader {
            id: loader
            anchors.fill: parent
        }
    }

    Component {
        id: loadingComp
        LoadingState {
            objectName: "settings.about.loading"
            title: "Cargando información"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.about.error"
            title: "Información no disponible"
            retryText: "Reintentar"
            onRetryRequested: root.state = "READY"
        }
    }

    Component {
        id: readyComp
        Flickable {
            anchors.fill: parent
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            objectName: "settings.about.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Acerca de"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Acerca de Michi"
                }

                Rectangle {
                    width: 80; height: 80; radius: MichiTheme.radiusXl
                    color: MichiTheme.colors.accentSurface
                    border.color: MichiTheme.colors.borderFocus
                    border.width: 1

                    Text {
                        anchors.centerIn: parent
                        text: "MM"
                        color: MichiTheme.colors.accentBlue
                        font.pixelSize: MichiTheme.typography.heroTitleSize
                        font.weight: MichiTheme.typography.weightBold
                        font.letterSpacing: 2.0
                        opacity: 0.50
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "Michi Music Player"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }

                    Text {
                        text: "Versión 2.5.0"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                    }

                    Text {
                        text: "Basado en Miro Player (GPL-3.0)"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Información del sistema"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Repeater {
                        model: [
                            { label: "Sistema operativo", value: "Linux 6.x" },
                            { label: "Arquitectura", value: "x86_64" },
                            { label: "Qt", value: "6.7" },
                            { label: "PySide6", value: "6.7.2" },
                            { label: "GStreamer", value: "1.28" },
                            { label: "Backend de audio", value: "GStreamer + MPD" }
                        ]

                        RowLayout {
                            width: parent.width
                            spacing: MichiTheme.spacing.md

                            Text {
                                text: modelData.label + ":"
                                color: MichiTheme.colors.textSecondary
                                font.pixelSize: MichiTheme.typography.bodySize
                                Layout.fillWidth: true
                            }

                            Text {
                                text: modelData.value
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                font.weight: MichiTheme.typography.weightMedium
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Licencia"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Text {
                        text: "GNU General Public License v3.0 o posterior"
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Créditos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Text {
                        text: "Desarrollado por pitydah\nBasado en Miro Player por C. H. y contribuyentes."
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize
                        wrapMode: Text.WordWrap
                        width: parent.width
                        lineHeight: 1.5
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Enlaces"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Repositorio"
                            color: MichiTheme.colors.accentBlue
                            font.pixelSize: MichiTheme.typography.bodySize
                            Accessible.name: "Repositorio GitHub"
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Qt.openUrlExternally("https://github.com/pitydah/michi-music-player")
                            }
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            id: updatesBtn
                            objectName: "settings.about.checkUpdates"
                            text: "Buscar actualizaciones"
                            variant: "primary"
                            Accessible.name: "Buscar actualizaciones"
                            KeyNavigation.tab: closeBtn
                            onClicked: root.checkUpdates()
                        }
                    }

                    Text {
                        text: "Documentación · Reportar un problema · Licencia"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Text {
                    text: "© 2026 Michi Music Player. GPL-3.0-or-later."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.captionSize
                    horizontalAlignment: Text.AlignHCenter
                    width: parent.width
                }

                MichiButton {
                    id: closeBtn
                    objectName: "settings.about.close"
                    text: "Cerrar"
                    variant: "ghost"
                    anchors.horizontalCenter: parent.horizontalCenter
                    Accessible.name: "Cerrar acerca de"
                    KeyNavigation.tab: updatesBtn
                    onClicked: root.closeRequested()
                }
            }
        }
    }
}
