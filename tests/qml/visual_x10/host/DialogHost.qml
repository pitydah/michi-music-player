import QtQuick
import QtQuick.Controls
import QtQuick.Window

import ui_qml.theme
import ui_qml.components

Window {
    id: root
    visible: false
    width: 640
    height: 480
    title: "Dialog Host"

    property alias dialog: dialog

    MichiDialog {
        id: dialog
        objectName: "testDialog"
        buttons: [
            MichiButton { text: "Aceptar"; objectName: "acceptBtn" },
            MichiButton { text: "Cancelar"; objectName: "cancelBtn" }
        ]
    }
}
