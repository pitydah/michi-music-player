import QtQuick
import QtQuick.Controls
import "../../theme"

TextField {
    focusPolicy: Qt.StrongFocus
    id: root

    property var bridge: null

    placeholderText: "Buscar canciones, álbumes, artistas..."
    width: 240
    onTextChanged: {
        if (root.bridge && typeof root.bridge.search !== "undefined")
            root.bridge.search(text)
    }
}
