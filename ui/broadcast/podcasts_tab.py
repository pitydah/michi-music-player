"""PodcastsTab — grid of subscribed podcast shows with actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QMenu, QMessageBox, QFileDialog,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss
from streaming.podcast_manager import PodcastManager
from streaming.podcast_models import PodcastShow


class PodcastsTab(QWidget):
    add_feed_requested = Signal()
    show_selected = Signal(int)

    def __init__(self, podcast_manager: PodcastManager | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("podcastsTab")
        self._pm = podcast_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        self._cl = QVBoxLayout(content)
        self._cl.setContentsMargins(0, 0, 0, 0)
        self._cl.setSpacing(12)

        self._empty_state = QLabel(
            "No hay podcasts suscritos.\n\n"
            'Usa el boton "+ Anadir podcast RSS" para suscribirte '
            "a tu primer programa."
        )
        self._empty_state.setAlignment(Qt.AlignCenter)
        self._empty_state.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 13px; "
            "background: transparent; border: none; padding: 48px;"
        )
        self._empty_state.setWordWrap(True)
        self._cl.addWidget(self._empty_state)

        self._grid = QGridLayout()
        self._grid.setSpacing(14)
        self._cl.addLayout(self._grid)

        action_row = QHBoxLayout()
        self._refresh_all_btn = QPushButton("Actualizar todos")
        self._refresh_all_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_all_btn.setStyleSheet(glass_button_qss("ghost"))
        self._refresh_all_btn.clicked.connect(self._refresh_all)
        action_row.addWidget(self._refresh_all_btn)

        self._import_opml_btn = QPushButton("Importar OPML")
        self._import_opml_btn.setCursor(Qt.PointingHandCursor)
        self._import_opml_btn.setStyleSheet(glass_button_qss("ghost"))
        self._import_opml_btn.clicked.connect(self._import_opml)
        action_row.addWidget(self._import_opml_btn)

        self._export_opml_btn = QPushButton("Exportar OPML")
        self._export_opml_btn.setCursor(Qt.PointingHandCursor)
        self._export_opml_btn.setStyleSheet(glass_button_qss("ghost"))
        self._export_opml_btn.clicked.connect(self._export_opml)
        action_row.addWidget(self._export_opml_btn)

        action_row.addStretch()
        self._cl.addLayout(action_row)

        self._cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.reload()

    def reload(self):
        if self._pm is None:
            self._empty_state.setVisible(True)
            return
        shows = self._pm.get_shows()
        if not shows:
            self._empty_state.setVisible(True)
            self._clear_grid()
            return
        self._empty_state.setVisible(False)
        self._clear_grid()
        for i, show in enumerate(shows):
            card = ShowCard(show, self._pm, self)
            card.show_episodes.connect(self.show_selected.emit)
            self._grid.addWidget(card, i // 2, i % 2)

    def set_filter(self, text: str):
        if self._pm is None:
            return
        shows = self._pm.get_shows()
        self._clear_grid()
        idx = 0
        for show in shows:
            if text.lower() in show.title.lower() or text.lower() in show.author.lower():
                card = ShowCard(show, self._pm, self)
                card.show_episodes.connect(self.show_selected.emit)
                self._grid.addWidget(card, idx // 2, idx % 2)
                idx += 1
        self._empty_state.setVisible(idx == 0)

    def _refresh_all(self):
        if self._pm is None:
            return
        self._refresh_all_btn.setEnabled(False)
        self._refresh_all_btn.setText("Actualizando...")
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        result = self._pm.refresh_all()
        self.reload()
        self._refresh_all_btn.setEnabled(True)
        self._refresh_all_btn.setText("Actualizar todos")
        msg = f"Actualizados: {result['refreshed']}, nuevos: {result['new_episodes']}"
        if result["errors"]:
            msg += f"\nErrores: {len(result['errors'])}"
        QMessageBox.information(self, "Actualizar podcasts", msg)

    def _import_opml(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Importar OPML", "", "OPML (*.opml *.xml);;Todos (*)"
        )
        if not fp:
            return
        from streaming.opml import import_opml
        result = import_opml(fp)
        if not result["ok"]:
            QMessageBox.warning(self, "Importar OPML", "\n".join(result["errors"]))
            return
        imported = 0
        skipped = 0
        for feed_url in result["feeds"]:
            r = self._pm.add_feed(feed_url, import_limit=50)
            if r.get("ok"):
                imported += 1
            else:
                skipped += 1
        QMessageBox.information(
            self, "Importar OPML",
            f"Importados: {imported}\nYa suscritos/saltados: {skipped}"
        )
        self.reload()

    def _export_opml(self):
        if self._pm is None:
            return
        shows = self._pm.get_shows()
        if not shows:
            QMessageBox.information(self, "Exportar OPML", "No hay podcasts para exportar.")
            return
        fp, _ = QFileDialog.getSaveFileName(
            self, "Exportar OPML", "subscriptions.opml", "OPML (*.opml);;XML (*.xml)"
        )
        if not fp:
            return
        from streaming.opml import export_opml
        content = export_opml(shows)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        QMessageBox.information(self, "Exportar OPML", f"{len(shows)} podcast(s) exportados.")

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ShowCard(QFrame):
    show_episodes = Signal(int)

    def __init__(self, show: PodcastShow, pm: PodcastManager | None, parent=None):
        super().__init__(parent)
        self._show = show
        self._pm = pm
        self.setStyleSheet(glass_card_qss("podcastCard"))
        self.setMinimumHeight(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        title = QLabel(show.title)
        title.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        if show.author:
            author = QLabel(show.author)
            author.setStyleSheet(
                "color: rgba(255,255,255,0.50); font-size: 11px; "
                "background: transparent; border: none;"
            )
            layout.addWidget(author)

        meta = QLabel(
            f"{show.episode_count} episodio(s)"
            + (f", {show.unread_count} nuevo(s)" if show.unread_count else "")
        )
        meta.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 10px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(meta)

        if show.unread_count:
            badge = QLabel(f"{show.unread_count} NUEVO(S)")
            badge.setStyleSheet(
                "color: rgba(100,220,100,0.90); font-size: 9px; font-weight: 700; "
                "background: rgba(100,220,100,0.10); "
                "border: 1px solid rgba(100,220,100,0.15); "
                "border-radius: 4px; padding: 2px 8px;"
            )
            layout.addWidget(badge)

        btn_row = QHBoxLayout()
        view_btn = QPushButton("Ver episodios")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(glass_button_qss("primary"))
        view_btn.clicked.connect(lambda: self.show_episodes.emit(show.id))
        btn_row.addWidget(view_btn)

        menu_btn = QPushButton("\u00b7\u00b7\u00b7")
        menu_btn.setCursor(Qt.PointingHandCursor)
        menu_btn.setFixedWidth(32)
        menu_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; "
            "color: rgba(255,255,255,0.50); font-size: 14px; }"
        )
        menu_btn.clicked.connect(self._show_menu)
        btn_row.addWidget(menu_btn)

        layout.addLayout(btn_row)

    def _show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #090B11; border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 8px; padding: 4px; }"
            "QMenu::item { color: rgba(255,255,255,0.78); font-size: 11px; "
            "padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:hover { background: rgba(143,183,255,0.10); }"
        )
        play_latest = menu.addAction("Reproducir ultimo no escuchado")
        refresh = menu.addAction("Actualizar feed")
        fav_action = menu.addAction("Quitar favorito" if self._show.favorite else "Marcar favorito")
        menu.addSeparator()
        web = menu.addAction("Abrir sitio web")
        copy_rss = menu.addAction("Copiar RSS")
        menu.addSeparator()
        delete = menu.addAction("Eliminar suscripcion")

        action = menu.exec(
            self.sender().mapToGlobal(Qt.DevicePixelRatio) if self.sender()
            else self.mapToGlobal(self.rect().topRight())
        )
        if action is None:
            return
        if action == play_latest:
            latest = self._pm.get_latest_unplayed_for_show(self._show.id) if self._pm else None
            if latest:
                from PySide6.QtCore import QCoreApplication
                QCoreApplication.postEvent(self.parent(), None)
        elif action == refresh:
            if self._pm:
                self._pm.refresh_feed(self._show.id)
                p = self.parent()
                if p and hasattr(p, 'reload'):
                    p.reload()
        elif action == fav_action:
            if self._pm:
                self._pm._repo._conn.execute(
                    "UPDATE podcast_shows SET favorite=? WHERE id=?",
                    (0 if self._show.favorite else 1, self._show.id),
                )
                self._pm._repo._conn.commit()
        elif action == web and self._show.website:
            import webbrowser
            webbrowser.open(self._show.website)
        elif action == copy_rss:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(self._show.feed_url)
        elif action == delete:
            reply = QMessageBox.question(
                self, "Eliminar suscripcion",
                f"Eliminar '{self._show.title}'?\n"
                "Los episodios descargados se conservaran.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes and self._pm:
                self._pm.remove_show(self._show.id)
                p = self.parent()
                if p and hasattr(p, 'reload'):
                    p.reload()
