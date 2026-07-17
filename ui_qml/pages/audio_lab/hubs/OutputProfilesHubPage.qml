import QtQuick

Item {
    objectName: "audioLabOutputProfilesHub"

    Loader {
        anchors.fill: parent
        source: "../../outputs/OutputProfilesPage.qml"
    }
}
