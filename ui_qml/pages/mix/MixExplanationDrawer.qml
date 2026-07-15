import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

<<<<<<< Updated upstream
Item {
=======
<<<<<<< HEAD
Drawer {
>>>>>>> Stashed changes
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _mixParams: ({})
    property var _trackExplanations: []
    property bool _open: false

    signal closed()

    objectName: "MixExplanationDrawer"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Explicación del Mix"

<<<<<<< Updated upstream
=======
    onOpened: {
        if (root.mx && typeof root.mx.explainCurrentMix !== "undefined") {
            var exp = root.mx.explainCurrentMix()
            if (exp && exp.ok) {
                root._reasons = exp.reasons || []
                root._totalCandidates = exp.total || 0
                root._hasReasons = exp.has_reasons || false
            }
        }
        if (root.mx && typeof root.mx.partialFailureReport !== "undefined") {
            var pf = root.mx.partialFailureReport()
            if (pf && pf.ok) {
                root._partialResult = pf.has_failures || false
=======
Item {
    id: root

    property var mx: typeof mixBridge !== "undefined" ? mixBridge : null
    property var _mixParams: ({})
    property var _trackExplanations: []
    property bool _open: false

    signal closed()

    objectName: "MixExplanationDrawer"

    Accessible.role: Accessible.Dialog
    Accessible.name: "Explicación del Mix"

>>>>>>> Stashed changes
    function show(mixParams, trackExplanations) {
        root._mixParams = mixParams || {}
        root._trackExplanations = trackExplanations || []
        root._open = true
    }

    function dismiss() {
        root._open = false
        root.closed()
    }

    function loadExplanation() {
        if (root.mx && typeof root.mx.explainCurrentMix === "function") {
            var result = root.mx.explainCurrentMix()
            if (result && result.ok) {
                root._mixParams = { reasons: result.reasons || [], total: result.total || 0 }
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
            }
        }
    }

<<<<<<< Updated upstream
    Rectangle {
=======
<<<<<<< HEAD
    background: Rectangle {
        color: MichiTheme.colors.surfaceCard
        border.color: MichiTheme.colors.borderCard
        border.width: MichiTheme.borderWidth
    }

    Column {
>>>>>>> Stashed changes
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        visible: root._open
        opacity: root._open ? 1.0 : 0.0
        z: 10

        Behavior on opacity { NumberAnimation { duration: MichiTheme.motion.normal } }

        MouseArea {
            anchors.fill: parent
            onClicked: root.dismiss()
        }

        Rectangle {
            id: drawerPanel
            width: parent.width * 0.40
            height: parent.height
            anchors.right: parent.right
            color: MichiTheme.colors.surfaceCardElevated
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
            radius: 0

            Column {
                anchors.fill: parent; spacing: MichiTheme.spacing.md

                Rectangle {
                    width: parent.width; height: 48
                    color: "transparent"

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Explicación del Mix"; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { width: parent.width - dismissBtn.width - MichiTheme.spacing.lg - 60; height: 1 }

                        Text {
                            id: dismissBtn
                            text: "[X] Cerrar"; color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                            objectName: "explanationDrawerDismissBtn"
                            Accessible.name: "Cerrar explicación"
                            activeFocusOnTab: true

                            Keys.onReturnPressed: root.dismiss()
                            Keys.onSpacePressed: root.dismiss()
                            Keys.onEscapePressed: root.dismiss()

                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: root.dismiss()
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Flickable {
                    width: parent.width; height: parent.height - 100
                    contentHeight: contentCol.height + MichiTheme.spacing.xl
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    activeFocusOnTab: true

                    Column {
                        id: contentCol
                        width: parent.width - MichiTheme.spacing.xl * 2
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiTheme.spacing.lg

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Parámetros del Mix"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                            }

                            Repeater {
                                model: {
                                    var keys = Object.keys(root._mixParams)
                                    var items = []
                                    for (var i = 0; i < keys.length; i++) {
                                        var v = root._mixParams[keys[i]]
                                        if (Array.isArray(v)) {
                                            if (v.length > 0) items.push({ key: keys[i], value: v.join(", ") })
                                        } else if (typeof v === "boolean") {
                                            items.push({ key: keys[i], value: v ? "Sí" : "No" })
                                        } else if (v !== null && v !== undefined) {
                                            items.push({ key: keys[i], value: String(v) })
                                        }
                                    }
                                    return items
                                }

                                delegate: Row {
                                    width: parent.width; spacing: MichiTheme.spacing.sm
                                    Text {
                                        width: parent.width * 0.35
                                        text: modelData.key; color: MichiTheme.colors.textSecondary
                                        font.pixelSize: MichiTheme.typography.metaSize
                                    }
                                    Text {
                                        width: parent.width * 0.60
                                        text: modelData.value; color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            Text {
                                text: root._trackExplanations.length === 0
                                    ? (root._mixParams.reasons ? "Razones: " + root._mixParams.reasons.join(", ") : "Sin parámetros disponibles")
                                    : ""
                                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                                wrapMode: Text.WordWrap; width: parent.width
                                visible: text !== ""
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Reglas aplicadas por canción"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                                visible: root._trackExplanations.length > 0
                            }

                            Repeater {
                                model: root._trackExplanations

                                delegate: Rectangle {
                                    width: parent.width; height: 48
                                    color: MichiTheme.colors.surfaceCard
                                    radius: MichiTheme.radiusSm
                                    border.width: MichiTheme.borderWidth
                                    border.color: MichiTheme.colors.borderSubtle

                                    Row {
                                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                                        Text {
                                            width: parent.width * 0.40; text: modelData.title || ""
                                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                        }

                                        Text {
                                            width: parent.width * 0.50; text: modelData.reason || ""
                                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                            wrapMode: Text.WordWrap; anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

<<<<<<< Updated upstream
    Keys.onEscapePressed: {
        if (root._open) root.dismiss()
=======
        SectionHeader { text: "Reglas de selección"; width: parent.width }

        ListView {
            width: parent.width
            height: Math.min(contentHeight, 300)
            model: root._reasons
            clip: true
            spacing: 4

            delegate: Row {
                spacing: MichiTheme.spacing.sm
                width: parent.width

                Text {
                    text: "•"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: modelData
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                    wrapMode: Text.WordWrap
                    width: parent.width - 20
                }
            }

            Text {
                anchors.centerIn: parent
                visible: parent.count === 0
                text: "No hay reglas de selección disponibles para este mix."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
=======
    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.overlayDark
        visible: root._open
        opacity: root._open ? 1.0 : 0.0
        z: 10

        Behavior on opacity { NumberAnimation { duration: MichiTheme.motion.normal } }

        MouseArea {
            anchors.fill: parent
            onClicked: root.dismiss()
        }

        Rectangle {
            id: drawerPanel
            width: parent.width * 0.40
            height: parent.height
            anchors.right: parent.right
            color: MichiTheme.colors.surfaceCardElevated
            border.width: MichiTheme.borderWidth
            border.color: MichiTheme.colors.borderCard
            radius: 0

            Column {
                anchors.fill: parent; spacing: MichiTheme.spacing.md

                Rectangle {
                    width: parent.width; height: 48
                    color: "transparent"

                    Row {
                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: "Explicación del Mix"; color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightSemiBold
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { width: parent.width - dismissBtn.width - MichiTheme.spacing.lg - 60; height: 1 }

                        Text {
                            id: dismissBtn
                            text: "[X] Cerrar"; color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                            objectName: "explanationDrawerDismissBtn"
                            Accessible.name: "Cerrar explicación"
                            activeFocusOnTab: true

                            Keys.onReturnPressed: root.dismiss()
                            Keys.onSpacePressed: root.dismiss()
                            Keys.onEscapePressed: root.dismiss()

                            MouseArea {
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: root.dismiss()
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width; height: 1
                    color: MichiTheme.colors.borderSubtle
                }

                Flickable {
                    width: parent.width; height: parent.height - 100
                    contentHeight: contentCol.height + MichiTheme.spacing.xl
                    clip: true; boundsBehavior: Flickable.StopAtBounds
                    activeFocusOnTab: true

                    Column {
                        id: contentCol
                        width: parent.width - MichiTheme.spacing.xl * 2
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: MichiTheme.spacing.lg

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Parámetros del Mix"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                            }

                            Repeater {
                                model: {
                                    var keys = Object.keys(root._mixParams)
                                    var items = []
                                    for (var i = 0; i < keys.length; i++) {
                                        var v = root._mixParams[keys[i]]
                                        if (Array.isArray(v)) {
                                            if (v.length > 0) items.push({ key: keys[i], value: v.join(", ") })
                                        } else if (typeof v === "boolean") {
                                            items.push({ key: keys[i], value: v ? "Sí" : "No" })
                                        } else if (v !== null && v !== undefined) {
                                            items.push({ key: keys[i], value: String(v) })
                                        }
                                    }
                                    return items
                                }

                                delegate: Row {
                                    width: parent.width; spacing: MichiTheme.spacing.sm
                                    Text {
                                        width: parent.width * 0.35
                                        text: modelData.key; color: MichiTheme.colors.textSecondary
                                        font.pixelSize: MichiTheme.typography.metaSize
                                    }
                                    Text {
                                        width: parent.width * 0.60
                                        text: modelData.value; color: MichiTheme.colors.textPrimary
                                        font.pixelSize: MichiTheme.typography.bodySize
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            Text {
                                text: root._trackExplanations.length === 0
                                    ? (root._mixParams.reasons ? "Razones: " + root._mixParams.reasons.join(", ") : "Sin parámetros disponibles")
                                    : ""
                                color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
                                wrapMode: Text.WordWrap; width: parent.width
                                visible: text !== ""
                            }
                        }

                        Column { spacing: MichiTheme.spacing.sm; width: parent.width
                            Text {
                                text: "Reglas aplicadas por canción"; color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightMedium
                                visible: root._trackExplanations.length > 0
                            }

                            Repeater {
                                model: root._trackExplanations

                                delegate: Rectangle {
                                    width: parent.width; height: 48
                                    color: MichiTheme.colors.surfaceCard
                                    radius: MichiTheme.radiusSm
                                    border.width: MichiTheme.borderWidth
                                    border.color: MichiTheme.colors.borderSubtle

                                    Row {
                                        anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                                        Text {
                                            width: parent.width * 0.40; text: modelData.title || ""
                                            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize
                                            elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                                        }

                                        Text {
                                            width: parent.width * 0.50; text: modelData.reason || ""
                                            color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                                            wrapMode: Text.WordWrap; anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Keys.onEscapePressed: {
        if (root._open) root.dismiss()
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    }
}
