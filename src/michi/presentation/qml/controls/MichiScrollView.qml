import QtQuick
import QtQuick.Controls.Basic

ScrollView {
    id: root
    clip: true
    ScrollBar.vertical: MichiScrollBar { }
    ScrollBar.horizontal: MichiScrollBar { }
}
