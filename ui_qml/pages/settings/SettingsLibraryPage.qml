import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var bridge: typeof settingsBridgeV2 !== "undefined" ? settingsBridgeV2 : (typeof settingsBridge !== "undefined" ? settingsBridge : null)
    property var sourcesBridge: typeof librarySourcesBridge !== "undefined" ? librarySourcesBridge : null
    property string state: "READY"

    objectName: "settings.library"
    Accessible.role: Accessible.Panel
    Accessible.name: "Biblioteca"
    Accessible.description: "Carpetas musicales, escaneo y metadatos"

    signal closeRequested()

    states: [
        State { name: "LOADING"; PropertyChanges { target: loader; sourceComponent: loadingComp } },
        State { name: "READY"; PropertyChanges { target: loader; sourceComponent: readyComp } },
        State { name: "ERROR"; PropertyChanges { target: loader; sourceComponent: errorComp } }
    ]
    state: root.bridge ? "READY" : "ERROR"

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
            objectName: "settings.library.loading"
            title: "Cargando ajustes de biblioteca"
        }
    }

    Component {
        id: errorComp
        ErrorState {
            objectName: "settings.library.error"
            title: "Ajustes no disponibles"
            message: "No se pudo conectar con el servicio de configuración."
            retryText: "Reintentar"
            onRetryRequested: root.state = root.bridge ? "READY" : "ERROR"
        }
    }

    Component {
        id: readyComp
        Flickable {
            anchors.fill: parent
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            objectName: "settings.library.flickable"

            Keys.onEscapePressed: root.closeRequested()

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg
                topPadding: MichiTheme.spacing.xl
                leftPadding: MichiTheme.spacing.xl
                rightPadding: MichiTheme.spacing.xl

                Text {
                    text: "Biblioteca"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                    Accessible.name: "Sección Biblioteca"
                }

                Text {
                    text: "Carpetas, escaneo y organización de la biblioteca musical"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Carpetas musicales"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Rectangle {
                        width: parent.width
                        height: sourcesList.height + MichiTheme.spacing.md
                        color: MichiTheme.colors.surfaceCard
                        radius: MichiTheme.radiusMd
                        border.color: MichiTheme.colors.borderSubtle

                        ListView {
                            id: sourcesList
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.sm
                            clip: true
                            spacing: 2
                            model: root.sourcesBridge ? root.sourcesBridge.sources : []
                            objectName: "settings.library.folderList"
                            Accessible.name: "Lista de carpetas musicales"

                            delegate: Rectangle {
                                width: parent.width
                                height: 36
                                color: "transparent"
                                radius: MichiTheme.radiusSm

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: MichiTheme.spacing.sm
                                    spacing: MichiTheme.spacing.sm

                                    Text {
                                        text: modelData.path || ""
                                        color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.captionSize
                                        elide: Text.ElideMiddle
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: modelData.available ? "" : "(no disponible)"
                                        color: MichiTheme.colors.error
                                        font.pixelSize: MichiTheme.typography.captionSize
                                        visible: !modelData.available
                                    }
                                }
                            }

                            Item {
                                anchors.centerIn: parent
                                visible: sourcesList.count === 0
                                Text {
                                    text: "No hay carpetas configuradas"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.bodySize
                                }
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.sm

                        MichiButton {
                            id: addFolderBtn
                            objectName: "settings.library.addFolder"
                            text: "Añadir carpeta"
                            variant: "primary"
                            Accessible.name: "Añadir carpeta musical"
                            KeyNavigation.tab: watchSwitch
                        }

                        Item { Layout.fillWidth: true }

                        MichiButton {
                            id: rescanBtn
                            objectName: "settings.library.rescan"
                            text: "Reescanear"
                            variant: "secondary"
                            Accessible.name: "Reescanear biblioteca"
                            KeyNavigation.tab: clearRescanBtn
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Escaneo automático"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Vigilar cambios en carpetas"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: watchSwitch
                            objectName: "settings.library.watchFolders"
                            checked: true
                            Accessible.name: "Vigilar cambios en carpetas"
                            Accessible.description: "Detectar cambios automáticamente"
                            KeyNavigation.tab: autoScanSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Escaneo automático al iniciar"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: autoScanSwitch
                            objectName: "settings.library.autoScan"
                            checked: true
                            Accessible.name: "Escaneo automático al iniciar"
                            KeyNavigation.tab: indexerModeCombo
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Modo de indexación"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        ComboBox {
                            id: indexerModeCombo
                            objectName: "settings.library.indexerMode"
                            model: ["Rápido", "Completo", "Profundo"]
                            currentIndex: 1
                            Accessible.name: "Modo de indexación"
                            KeyNavigation.tab: coverArtSwitch
                        }
                    }
                }

                Column {
                    width: parent.width
                    spacing: MichiTheme.spacing.md

                    Text {
                        text: "Carátulas y metadatos"
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Extraer carátulas incrustadas"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: coverArtSwitch
                            objectName: "settings.library.coverArtExtraction"
                            checked: true
                            Accessible.name: "Extraer carátulas incrustadas"
                            KeyNavigation.tab: metadataEnrichmentSwitch
                        }
                    }

                    RowLayout {
                        width: parent.width
                        spacing: MichiTheme.spacing.md

                        Text {
                            text: "Enriquecimiento de metadatos"
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.bodySize
                            Layout.fillWidth: true
                        }

                        Switch {
                            id: metadataEnrichmentSwitch
                            objectName: "settings.library.metadataEnrichment"
                            checked: true
                            Accessible.name: "Enriquecimiento de metadatos"
                            Accessible.description: "Completar metadatos desde fuentes externas"
                            KeyNavigation.tab: addFolderBtn
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
                        text: "Acciones destructivas"
                        color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.sectionTitleSize
                        font.weight: MichiTheme.typography.weightMedium
                    }

                    Text {
                        text: "Estas acciones no se pueden deshacer."
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                    }

                    MichiButton {
                        id: clearRescanBtn
                        objectName: "settings.library.clearAndRescan"
                        text: "Limpiar y reescanear"
                        variant: "danger"
                        Accessible.name: "Limpiar y reescanear biblioteca"
                        Accessible.description: "Elimina todos los datos indexados y vuelve a escanear. Acción destructiva."
                        KeyNavigation.tab: addFolderBtn
                        onClicked: confirmClearRescanDialog.open()
                    }
                }
            }
        }
    }

    ConfirmActionDialog {
        id: confirmClearRescanDialog
        objectName: "settings.library.clearRescanConfirm"
        title: "Limpiar y reescanear"
        message: "¿Estás seguro? Esto eliminará todos los datos indexados de la biblioteca y volverá a escanear todas las carpetas. Esta acción no se puede deshacer."
        confirmText: "Limpiar y reescanear"
        danger: true
        onConfirmed: {
            console.log("[Settings] Limpiar y reescanear biblioteca")
        }
    }
}
