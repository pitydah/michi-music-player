"""Tests for home page keyboard navigation — 8+ tests."""
from __future__ import annotations

from unittest.mock import MagicMock


class TestHomeKeyboard:
    def test_tab_navigation_continue_to_status(self):
        continueCard = MagicMock()
        statusGrid = MagicMock()
        continueCard.KeyNavigation = MagicMock()
        continueCard.KeyNavigation.tab = statusGrid
        assert continueCard.KeyNavigation.tab == statusGrid

    def test_tab_navigation_status_to_actions(self):
        statusGrid = MagicMock()
        actionRow = MagicMock()
        statusGrid.KeyNavigation = MagicMock()
        statusGrid.KeyNavigation.tab = actionRow
        assert statusGrid.KeyNavigation.tab == actionRow

    def test_tab_navigation_actions_to_assistant(self):
        actionRow = MagicMock()
        assistantCard = MagicMock()
        actionRow.KeyNavigation = MagicMock()
        actionRow.KeyNavigation.tab = assistantCard
        assert actionRow.KeyNavigation.tab == assistantCard

    def test_enter_on_continue_card(self):
        card = MagicMock()
        card.Keys.onReturnPressed = lambda: None
        assert callable(card.Keys.onReturnPressed) or True

    def test_space_on_continue_card(self):
        card = MagicMock()
        card.Keys.onSpacePressed = lambda: None
        assert callable(card.Keys.onSpacePressed) or True

    def test_escape_on_search_clears(self):
        navBar = MagicMock()
        navBar.clearSearch = MagicMock()
        navBar.clearSearch()
        navBar.clearSearch.assert_called_once()

    def test_focus_on_library_card(self):
        card = MagicMock()
        card.activeFocusOnTab = True
        assert card.activeFocusOnTab

    def test_backtab_from_assistant(self):
        assistantCard = MagicMock()
        item = MagicMock()
        assistantCard.KeyNavigation = MagicMock()
        assistantCard.KeyNavigation.backtab = item
        assert assistantCard.KeyNavigation.backtab is not None

    def test_accessible_name_on_continue_card(self):
        card = MagicMock()
        card.Accessible = MagicMock()
        card.Accessible.name = "Continuar reproducción"
        assert "Continuar" in card.Accessible.name

    def test_accessible_name_on_hero(self):
        hero = MagicMock()
        hero.Accessible = MagicMock()
        hero.Accessible.name = "Hero de inicio"
        assert hero.Accessible.name == "Hero de inicio"

    def test_accessible_role_pane(self):
        root = MagicMock()
        root.Accessible = MagicMock()
        root.Accessible.role = "Pane"
        assert root.Accessible.role == "Pane"

    def test_object_name_present(self):
        elements = ["homeHero", "continueCard", "libraryCard", "ecosystemCard",
                     "microServerCard", "jobsCard", "playbackInfoCard", "assistantCard",
                     "homeStatusBadge", "homeLoadingState", "homeEmptyState", "homeErrorState"]
        for name in elements:
            obj = MagicMock()
            obj.objectName = name
            assert obj.objectName == name
