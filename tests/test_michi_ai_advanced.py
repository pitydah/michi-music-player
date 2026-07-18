"""Tests for Michi AI advanced — intents, action validation, download as job, fallback."""
from unittest.mock import MagicMock, patch

import pytest


class TestMichiAIIntents:
    def test_intent_router_import(self):
        from michi_ai.v2.intent.intent_router_v2 import IntentRouterV2
        assert IntentRouterV2 is not None

    def test_intent_has_detect(self):
        from michi_ai.v2.intent.intent_router_v2 import IntentRouterV2
        router = IntentRouterV2()
        assert hasattr(router, 'detect')

    def test_action_registry_execute(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        assert hasattr(ar, 'execute')

    def test_no_direct_file_access(self):
        """Verify Michi AI tools don't access filesystem directly."""
        import ast, os
        tools_dir = "michi_ai/v2/tools"
        violations = []
        for fname in os.listdir(tools_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            with open(os.path.join(tools_dir, fname)) as f:
                content = f.read()
            if "os.remove" in content or "shutil.rmtree" in content or "os.unlink" in content:
                violations.append(fname)
        assert len(violations) == 0, f"Tools with direct FS access: {violations}"

    def test_action_registry_size(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        assert len(ar.actions) > 0

    def test_michi_ai_bridge_import(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        assert MichiAIBridge is not None

    def test_michi_ai_bridge_send_message(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        assert hasattr(MichiAIBridge, 'sendMessage')

    def test_michi_ai_bridge_cancel_download(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        assert hasattr(MichiAIBridge, 'cancelDownload')
