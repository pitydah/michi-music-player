import QtQuick
import QtQuick.Controls
import "theme"
import "components"
import "shell"
import "materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Michi App"
    objectName: "michiApp"
    focus: true
    id: appRoot

    property bool bridgesReady: false

    Component.onCompleted: {
        console.log("[MichiApp] QML Foundation loaded")
        bridgesReady = true
    }

    AppShell {
        id: shell
        anchors.fill: parent
        visible: bridgesReady
    }

    ToastHost {
        anchors.fill: parent
        z: 9999
    }

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: !bridgesReady

        Text {
            anchors.centerIn: parent
            color: MichiTheme.colors.accent
            font.pixelSize: 18
            text: "Inicializando Michi Music Player QML..."
        }
    }
}
