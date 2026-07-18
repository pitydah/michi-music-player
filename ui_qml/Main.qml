import QtQuick
import QtQuick.Window
import QtCore
import "theme"

Window {
    id: mainWindow
    visible: true
    width: 1440
    height: 900
    title: qsTr("Michi Music Player")
    color: MichiTheme.colors.bgApp
    minimumWidth: 1024
    minimumHeight: 640
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint

    Settings {
        id: appSettings
        category: "window"
    }

    Settings {
        id: appearanceSettings
        category: "appearance"
    }

    Shortcut {
        sequence: "F11"
        onActivated: {
            if (mainWindow.visibility === Window.FullScreen)
                mainWindow.showNormal()
            else
                mainWindow.showFullScreen()
        }
    }

    Component.onCompleted: {
        var w = appSettings.value("width", 1440)
        var h = appSettings.value("height", 900)
        var xPos = appSettings.value("x", -1)
        var yPos = appSettings.value("y", -1)
        if (xPos >= 0) mainWindow.x = xPos
        if (yPos >= 0) mainWindow.y = yPos
        mainWindow.width = w
        mainWindow.height = h
        if (appSettings.value("maximized", false))
            mainWindow.showMaximized()

        var darkMode = appearanceSettings.value("dark_mode", true)
        MichiTheme.setDarkMode(darkMode)
    }

    MichiApp {
        anchors.fill: parent
    }

    Component.onDestruction: {
        appSettings.setValue("width", mainWindow.width)
        appSettings.setValue("height", mainWindow.height)
        appSettings.setValue("x", mainWindow.x)
        appSettings.setValue("y", mainWindow.y)
        appSettings.setValue("maximized", mainWindow.visibility === Window.Maximized)
        appSettings.sync()
    }
}
