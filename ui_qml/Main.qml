import QtQuick
import QtQuick.Window
import "theme"

Window {
    id: mainWindow
    visible: true
    width: 1440
    height: 900
    title: "Michi Music Player"
    color: MichiTheme.colors.bgApp
    minimumWidth: 1024
    minimumHeight: 640
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint

    MichiApp {
        anchors.fill: parent
    }
}
