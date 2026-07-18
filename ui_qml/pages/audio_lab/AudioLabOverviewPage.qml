import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "audioLabOverviewPage"

    Accessible.role: Accessible.Pane
    Accessible.name: "Audio Lab"

    signal areaSelected(string areaKey)

    property var labService: typeof audioLabBridge !== "undefined" ? audioLabBridge : null
    property var overviewData: null
    property bool isLoading: true

    Component.onCompleted: {
        if (root.labService && root.labService.getOverviewData) {
            root.overviewData = root.labService.getOverviewData()
        }
        root.isLoading = false
    }

    // Estado de carga
    LoadingState {
        visible: root.isLoading
        anchors.centerIn: parent
        message: "Cargando Audio Lab..."
    }

    // Estado de error
    ErrorState {
        visible: !root.isLoading && (root.labService === null || root.overviewData === null)
        anchors.centerIn: parent
        message: root.labService === null ? "Bridge de Audio Lab no disponible" : "No se pudieron cargar los datos"
        onRetryRequested: {
            root.isLoading = true
            if (root.labService && root.labService.getOverviewData) {
                root.overviewData = root.labService.getOverviewData()
            }
            root.isLoading = false
        }
    }

    // Contenido principal
    Flickable {
        visible: !root.isLoading && root.labService !== null && root.overviewData !== null
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.xl
        contentHeight: column.height + MichiTheme.spacing.xxl
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        activeFocusOnTab: true

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.lg

            SectionHeader {
                width: parent.width
                text: "Audio Lab"
            }

            Text {
                width: parent.width
                text: "Herramientas profesionales para analizar, identificar, preservar y configurar tu audio"
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                wrapMode: Text.WordWrap
            }

            // Resumen de dependencias y trabajos
            Row {
                width: parent.width
                spacing: MichiTheme.spacing.sm

                StatusBadge {
                    kind: root.labService && root.labService.serviceAvailable ? "success" : "warning"
                    text: root.labService && root.labService.serviceAvailable ? "Audio Lab disponible" : "Audio Lab no disponible"
                }

                StatusBadge {
                    id: ffmpegBadge
                    kind: root.overviewData && root.overviewData.dependencies && root.overviewData.dependencies.ffmpeg ? "success" : "warning"
                    text: root.overviewData && root.overviewData.dependencies && root.overviewData.dependencies.ffmpeg ? "FFmpeg disponible" : "FFmpeg no disponible"
                }

                StatusBadge {
                    kind: root.overviewData && root.overviewData.dependencies && root.overviewData.dependencies.replaygain ? "success" : "warning"
                    text: root.overviewData && root.overviewData.dependencies && root.overviewData.dependencies.replaygain ? "ReplayGain disponible" : "ReplayGain no disponible"
                }

                Item { width: 1; height: 1; Layout.fillWidth: true }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.overviewData && root.overviewData.active_jobs > 0
                        ? root.overviewData.active_jobs + " trabajo(s) activo(s)"
                        : "Sin trabajos activos"
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.secondarySize
                }
            }

            // Grid de 5 tarjetas principales
            GridLayout {
                width: parent.width
                columns: parent.width > 1200 ? 3 : (parent.width > 800 ? 2 : 1)
                rowSpacing: MichiTheme.spacing.md
                columnSpacing: MichiTheme.spacing.md

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 180
                    radius: MichiTheme.radius.md
                    color: ma1.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: 1; border.color: MichiTheme.colors.borderCard
                    ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: "AN"; font.pixelSize: 20; color: MichiTheme.colors.accentBlue }
                        Text { text: "Diagnóstico"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Analiza, verifica integridad y compara archivos"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                    }
                    MouseArea { id: ma1; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("diagnostics"); Keys.onReturnPressed: clicked(); Keys.onSpacePressed: clicked() }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 180
                    radius: MichiTheme.radius.md
                    color: ma2.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: 1; border.color: MichiTheme.colors.borderCard
                    ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: "ID"; font.pixelSize: 20; color: MichiTheme.colors.accentBlue }
                        Text { text: "Identificador de Audios"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Identifica, corrige metadatos y carátulas"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                    }
                    MouseArea { id: ma2; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("identifier"); Keys.onReturnPressed: clicked(); Keys.onSpacePressed: clicked() }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 180
                    radius: MichiTheme.radius.md
                    color: ma3.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: 1; border.color: MichiTheme.colors.borderCard
                    ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: "BK"; font.pixelSize: 20; color: MichiTheme.colors.accentBlue }
                        Text { text: "Respaldar"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Convierte, normaliza, ripea y organiza"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                    }
                    MouseArea { id: ma3; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("backup"); Keys.onReturnPressed: clicked(); Keys.onSpacePressed: clicked() }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 180
                    radius: MichiTheme.radius.md
                    color: ma4.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: 1; border.color: MichiTheme.colors.borderCard
                    ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: "OP"; font.pixelSize: 20; color: MichiTheme.colors.accentBlue }
                        Text { text: "Perfiles de Salida"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Configura DAC, EQ y reproducción"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                    }
                    MouseArea { id: ma4; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("output_profiles"); Keys.onReturnPressed: clicked(); Keys.onSpacePressed: clicked() }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.columnSpan: 2; Layout.preferredHeight: 180
                    radius: MichiTheme.radius.md
                    color: ma5.containsMouse ? MichiTheme.colors.surfaceCardHover : MichiTheme.colors.surfaceCard
                    border.width: 1; border.color: MichiTheme.colors.borderCard
                    ColumnLayout { anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                        Text { text: "AI"; font.pixelSize: 20; color: MichiTheme.colors.accentBlue }
                        Text { text: "Inteligencia Local"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.cardTitleSize; font.weight: MichiTheme.typography.weightSemiBold }
                        Text { text: "Análisis acústico y automatización"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.secondarySize; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                    }
                    MouseArea { id: ma5; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.areaSelected("local_intelligence"); Keys.onReturnPressed: clicked(); Keys.onSpacePressed: clicked() }
                }
            }
        }
    }

    Connections {
        target: root
        function onAreaSelected(areaKey) {
            if (typeof navigationBridge === "undefined" || !navigationBridge) return
            var routeMap = {
                "diagnostics": "audio_lab.diagnostics",
                "identifier": "audio_lab.identifier",
                "backup": "audio_lab.backup",
                "output_profiles": "audio_lab.output_profiles",
                "local_intelligence": "audio_lab.local_intelligence"
            }
            var route = routeMap[areaKey] || "audio_lab"
            navigationBridge.navigate(route)
        }
    }
}
