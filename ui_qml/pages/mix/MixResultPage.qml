import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    objectName: "mixResult.page"

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _songs: root.mx ? root.mx.currentSongs : []
    property string _mixTitle: root.mx ? root.mx.currentMixTitle : "Mix"
    property string _errorMsg: ""

    signal backClicked()
    signal playAllClicked()
    signal enqueueAllClicked()
    signal savePlaylistClicked()

    Accessible.role: Accessible.Pane
    Accessible.name: "Resultado del mix"

    FocusScope {
        id: focusScope
        anchors.fill: parent
        activeFocusOnTab: true
        objectName: "mixResult.focusScope"

        Keys.onEscapePressed: root.backClicked()

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            spacing: MichiTheme.spacing.lg

            Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                MichiButton {
                    text: "< Volver"
                    variant: "ghost"
                    onClicked: root.backClicked()
                    objectName: "mixResult.backButton"
                    Accessible.name: "Volver"
                    KeyNavigation.tab: titleText
                }

                Text {
                    id: titleText
                    text: root._mixTitle
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                    anchors.verticalCenter: parent.verticalCenter
                    Accessible.role: Accessible.Heading
                    Accessible.name: root._mixTitle
                }
            }

            Text {
                text: root._errorMsg
                color: MichiTheme.colors.error
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root._errorMsg !== ""
                wrapMode: Text.WordWrap
                width: parent.width
                Accessible.role: Accessible.Alert
            }

            Row {
                spacing: MichiTheme.spacing.sm
                objectName: "mixResult.actions"

                MichiButton {
                    text: "Reproducir todo"
                    variant: "primary"
                    onClicked: {
                        if (root.mx && typeof root.mx.playMix !== "undefined")
                            root.mx.playMix()
                        root.playAllClicked()
                    }
                    objectName: "mixResult.playAllButton"
                    Accessible.name: "Reproducir todas las canciones"
                    KeyNavigation.tab: enqueueBtn
                }

                MichiButton {
                    id: enqueueBtn
                    text: "Agregar a cola"
                    variant: "secondary"
                    onClicked: {
                        if (root.mx && typeof root.mx.enqueueMix !== "undefined")
                            root.mx.enqueueMix()
                        root.enqueueAllClicked()
                    }
                    objectName: "mixResult.enqueueButton"
                    Accessible.name: "Agregar todas a la cola"
                    KeyNavigation.tab: saveBtn
                }

                MichiButton {
                    id: saveBtn
                    text: "Guardar como playlist"
                    variant: "ghost"
                    onClicked: root.savePlaylistClicked()
                    objectName: "mixResult.saveButton"
                    Accessible.name: "Guardar mix como playlist"
                    KeyNavigation.tab: trackList
                }
            }

            Text {
                text: root._songs.length + " canciones"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                visible: root._songs.length > 0
            }

            ListView {
                id: trackList
                width: parent.width
                height: parent.height - 220
                model: root._songs
                clip: true
                spacing: 1
                focus: true
                objectName: "mixResult.trackList"

                delegate: Rectangle {
                    width: parent.width
                    height: 40
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: MichiTheme.radiusSm
                    objectName: "mixResult.trackItem." + index

                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.title + " - " + (modelData.artist || "") + " - " + (modelData.album || "")

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: parent.width * 0.38
                            text: modelData.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: parent.width * 0.22
                            text: modelData.artist || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: parent.width * 0.15
                            text: modelData.album || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: 30
                            text: modelData.reason || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item {
                            width: 72
                            height: parent.height

                            Row {
                                anchors.centerIn: parent
                                spacing: 4

                                Text {
                                    text: "▶"
                                    color: MichiTheme.colors.accent
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    anchors.verticalCenter: parent.verticalCenter
                                    Accessible.name: "Reproducir"
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (root.mx && typeof root.mx.playFromIndex !== "undefined")
                                                root.mx.playFromIndex(index)
                                        }
                                    }
                                }

                                Text {
                                    text: "+"
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    anchors.verticalCenter: parent.verticalCenter
                                    Accessible.name: "Agregar a cola"
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (root.mx && typeof root.mx.enqueueTrack !== "undefined")
                                                root.mx.enqueueTrack(index)
                                        }
                                    }
                                }

                                Text {
                                    text: "◎"
                                    color: MichiTheme.colors.textMuted
                                    font.pixelSize: MichiTheme.typography.metaSize
                                    anchors.verticalCenter: parent.verticalCenter
                                    Accessible.name: "Abrir álbum"
                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (modelData.album_key && typeof navigationBridge !== "undefined" && navigationBridge)
                                                navigationBridge.navigateWithParams("library.album_detail", { album_key: modelData.album_key })
                                        }
                                    }
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: parent.count === 0
                    text: "Mix vacío. Genera un mix para ver resultados."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }

            MixFeedbackControls {
                width: parent.width
                visible: root._songs.length > 0
            }

            MixExplanationDrawer {
                id: explanationDrawer
                width: parent.width
                visible: false
            }
        }
    }

    Component.onCompleted: {
        if (root.mx) {
            root._songs = root.mx.currentSongs || []
            root._mixTitle = root.mx.currentMixTitle || "Mix"
            root._errorMsg = root.mx.errorMessage || ""
        }
    }
}
