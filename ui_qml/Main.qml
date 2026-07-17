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
        var settings = Qt.createQmlObject('import Qt.labs.settings; Settings {}', mainWindow)
        if (settings) {
            var w = settings.getValue("window/width", 1440)
            var h = settings.getValue("window/height", 900)
            var x = settings.getValue("window/x", -1)
            var y = settings.getValue("window/y", -1)
            if (x >= 0) mainWindow.x = x
            if (y >= 0) mainWindow.y = y
            mainWindow.width = w
            mainWindow.height = h
            if (settings.getValue("window/maximized", false))
                mainWindow.showMaximized()
        }
    }

    MichiApp {
        anchors.fill: parent
    }

    Component.onDestruction: {
        var settings = Qt.createQmlObject('import Qt.labs.settings; Settings {}', mainWindow)
        if (settings) {
            settings.setValue("window/width", mainWindow.width)
            settings.setValue("window/height", mainWindow.height)
            settings.setValue("window/x", mainWindow.x)
            settings.setValue("window/y", mainWindow.y)
            settings.setValue("window/maximized", mainWindow.visibility === Window.Maximized)
        }
    }
}
