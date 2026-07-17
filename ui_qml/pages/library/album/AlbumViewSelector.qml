// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"

RowLayout {
    id: root

    property int currentView: 0
    signal viewChanged(int index)

    spacing: MichiTheme.spacing.xs

    Repeater {
        model: [
            {label: "Grid", tooltip: "Vista cuadrícula"},
            {label: "Cover", tooltip: "Cover Flow"},
            {label: "Vinyl", tooltip: "Pared de vinilos"},
            {label: "Years", tooltip: "Línea de tiempo"},
            {label: "Mag", tooltip: "Revista"},
        ]

        MichiButton {
            Accessible.role: Accessible.Button

            activeFocusOnTab: true

            text: modelData.label
            variant: currentView === index ? "primary" : "ghost"
            Accessible.name: modelData.tooltip
            implicitHeight: 28
            onClicked: {
                root.currentView = index
                root.viewChanged(index)
            }
        }
    }
}
