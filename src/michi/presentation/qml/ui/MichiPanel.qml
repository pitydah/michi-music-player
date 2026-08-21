import QtQuick
import "../primitives" as Primitives

Primitives.MichiGlassSurface {
    default property alias content: root.contentData
    id: root
    elevation: "standard"
}
