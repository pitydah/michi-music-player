from __future__ import annotations
from legacy_widgets.ui.controllers.legacy_controllers import devices_controller as _mod
import sys
sys.modules["ui.controllers.devices_controller"] = _mod
