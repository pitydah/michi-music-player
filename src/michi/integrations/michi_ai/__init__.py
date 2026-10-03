"""Michi AI host adapter — optional, read-only baseline integration."""

from michi.integrations.michi_ai.composition import (
    PLAYER_AI_CAPABILITIES,
    PlayerMichiAIIntegration,
    build_player_michi_ai,
)
from michi.integrations.michi_ai.library_gateway import PlayerLibraryGateway

__all__ = [
    "PLAYER_AI_CAPABILITIES",
    "PlayerLibraryGateway",
    "PlayerMichiAIIntegration",
    "build_player_michi_ai",
]
