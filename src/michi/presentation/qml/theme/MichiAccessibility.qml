pragma Singleton
import QtQuick

QtObject {
    property bool reducedMotion: false
    property bool highContrast: false
    property string inputModality: "mouse"
    readonly property bool keyboardMode: inputModality === "keyboard"
    function noteKeyboard() { inputModality = "keyboard" }
    function notePointer() { inputModality = "mouse" }
}
