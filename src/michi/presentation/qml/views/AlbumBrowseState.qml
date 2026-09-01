import QtQuick

QtObject {
    property string currentKey: ""
    property real galleryContentY: 0
    property int galleryIndex: -1
    property int flowIndex: -1
    property real vinylContentY: 0
    property int vinylIndex: -1
    property real chronologyContentY: 0
    property int chronologyIndex: -1
    property real editorialContentY: 0
    property int editorialIndex: -1
    property real listContentY: 0
    property int listIndex: -1

    function remember(key) {
        if (key)
            currentKey = key
    }
}
