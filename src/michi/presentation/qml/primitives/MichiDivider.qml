import QtQuick
import "../theme"

Rectangle {
    property bool vertical: false
    implicitWidth: vertical ? 1 : 120
    implicitHeight: vertical ? 24 : 1
    color: MichiSemanticColors.borderSubtle
}
