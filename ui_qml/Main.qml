import QtQuick
import QtQuick.Window
import "theme"

Window {
    id: mainWindow
    visible: true
    width: 1440
    height: 900
    title: "Michi Music Player (QML Experimental)"
    color: MichiTheme.colors.bgApp
    minimumWidth: 1024
    minimumHeight: 640

    MichiApp {
        anchors.fill: parent
    }
}
