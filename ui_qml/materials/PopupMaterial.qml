import QtQuick

MichiBaseSurface {
    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Material emergente")
    objectName: "popupMaterial"
    id: root

    level: 4
    radius: MichiTheme.radius.lg
    borderVisible: true
}
