import QtQuick
import "../../theme"

Text {
    id: root

    property real seconds: 0
    property bool showMilliseconds: false

    function padded(value, digits) {
        var text = String(Math.floor(value))
        while (text.length < digits)
            text = "0" + text
        return text
    }

    function formattedTime() {
        var total = Math.max(0, Number(seconds))
        var hours = Math.floor(total / 3600)
        var minutes = Math.floor((total % 3600) / 60)
        var secs = Math.floor(total % 60)
        var result = padded(hours, 2) + ":" + padded(minutes, 2)
            + ":" + padded(secs, 2)
        if (showMilliseconds)
            result += "." + padded(Math.floor((total % 1) * 1000), 3)
        return result
    }

    text: formattedTime()
    color: MichiTheme.colors.textPrimary
    font.family: "monospace"
    font.pixelSize: MichiTheme.typography.displaySize
    font.weight: MichiTheme.typography.weightSemiBold
    Accessible.role: Accessible.StaticText
    Accessible.name: qsTr("Duración de grabación")
    Accessible.description: text
}
