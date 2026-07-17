import QtQuick

Item {
    id: root
    objectName: "audioLabBackupHub"

    Loader {
        anchors.fill: parent
        source: "../AudioBackupPage.qml"
    }
}
