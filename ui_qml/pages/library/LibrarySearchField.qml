import QtQuick
import QtQuick.Controls
import "../../theme"

TextField {
    Accessible.role: Accessible.EditableText

    Accessible.name: "Buscar en biblioteca"

    activeFocusOnTab: true

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
