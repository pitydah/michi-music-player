import QtQuick
import QtQuick.Controls
import "theme"
import "components"
import "shell"
import "materials"

Item {
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

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.bgApp
        visible: !bridgesReady

        Text {
            anchors.centerIn: parent
            color: "#8FB7FF"
            font.pixelSize: 18
            text: "Inicializando Michi Music Player QML..."
        }
    }
}
