import QtQuick
import QtQuick.Controls
import "theme"
import "components"
import "shell"
import "materials"

Item {
    id: appRoot

    property bool bridgesReady: false
    property bool fatalError: false
    property string fatalMessage: ""

    objectName: "michiApp"
    Accessible.role: Accessible.Application
    Accessible.name: "Michi Music Player"

    Component.onCompleted: {
        console.log("[MichiApp] QML Foundation loaded")
        bridgesReady = true
    }

    AppShell {
        id: shell
        anchors.fill: parent
        visible: bridgesReady && !fatalError
    }

    ToastHost {
        anchors.fill: parent
        z: 9999
    }

    Loader {
        anchors.fill: parent
        active: !bridgesReady && !fatalError
        visible: active
        z: 9998

        sourceComponent: Rectangle {
            color: MichiTheme.colors.bgApp

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.lg

                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    running: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: 18
                    text: "Inicializando Michi Music Player QML..."
                    Accessible.name: "Cargando Michi Music Player"
                }
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: fatalError
        visible: active
        z: 9999

        sourceComponent: Rectangle {
            color: MichiTheme.colors.bgApp

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.lg
                width: Math.min(400, parent.width * 0.8)

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Michi Music Player"
                    color: MichiTheme.colors.accentBlue
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightBold
                }

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 64; height: 64; radius: MichiTheme.radiusLg
                    color: MichiTheme.colors.error
                    opacity: 0.15

                    Text {
                        anchors.centerIn: parent
                        text: "!"
                        color: MichiTheme.colors.error
                        font.pixelSize: 32
                        font.weight: MichiTheme.typography.weightBold
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Error fatal"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: appRoot.fatalMessage
                    color: MichiTheme.colors.textSecondary
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    function showFatal(message) {
        fatalError = true
        fatalMessage = message
    }
}
