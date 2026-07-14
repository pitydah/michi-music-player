from __future__ import annotations

import logging
from core.service_container import ServiceContainer

logger = logging.getLogger("michi.application_bootstrap")


class ApplicationBootstrap:
    def __init__(self):
        self.container = ServiceContainer()

    def run(self):
        self._build_config()
        self._open_database()
        self._build_repositories()
        self._build_workers()
        self._build_settings()
        self._build_domain_services()
        self._build_action_registry()
        self._build_bridges()
        self._register_contexts()
        self._load_qml()
        self._lifecycle_ready()

    def _build_config(self):
        logger.info("ApplicationBootstrap: building config")

    def _open_database(self):
        logger.info("ApplicationBootstrap: opening database")

    def _build_repositories(self):
        logger.info("ApplicationBootstrap: building repositories")

    def _build_workers(self):
        logger.info("ApplicationBootstrap: building workers")

    def _build_settings(self):
        logger.info("ApplicationBootstrap: building settings")

    def _build_domain_services(self):
        logger.info("ApplicationBootstrap: building domain services")

    def _build_action_registry(self):
        logger.info("ApplicationBootstrap: building action registry")

    def _build_bridges(self):
        logger.info("ApplicationBootstrap: building bridges")

    def _register_contexts(self):
        logger.info("ApplicationBootstrap: registering contexts")

    def _load_qml(self):
        logger.info("ApplicationBootstrap: loading QML")

    def _lifecycle_ready(self):
        self.container.set_ready()
        logger.info("ApplicationBootstrap: lifecycle ready")
