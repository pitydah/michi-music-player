import QtQuick
import QtQuick.Controls
import "../../theme"

SearchField {
    id: root

    property var bridge: null

    placeholderText: "Buscar canciones, álbumes, artistas..."
    width: 240
    onSearchTextChanged: {
        if (root.bridge && typeof root.bridge.search !== "undefined")
            root.bridge.search(text)
    }
}
