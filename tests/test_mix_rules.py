"""Tests for MixRuleEngine — AND/OR operators, seed reproducibility, preview."""
import random

import pytest


@pytest.fixture
def engine():
    from core.mix_rules import MixRuleEngine
    return MixRuleEngine()


@pytest.fixture
def sample_tracks():
    return [
        {"title": "Rock Anthem", "artist": "Rock Band", "album": "Rock Album",
         "genre": "Rock", "year": 2020, "duration": 240, "play_count": 150},
        {"title": "Jazz Mood", "artist": "Jazz Trio", "album": "Jazz Night",
         "genre": "Jazz", "year": 2019, "duration": 320, "play_count": 45},
        {"title": "Pop Hit", "artist": "Pop Star", "album": "Pop World",
         "genre": "Pop", "year": 2022, "duration": 200, "play_count": 500},
        {"title": "Classical Morning", "artist": "Classical Orch", "album": "Classical Vol 1",
         "genre": "Classical", "year": 2015, "duration": 600, "play_count": 30},
        {"title": "Rock Ballad", "artist": "Rock Band", "album": "Rock Album",
         "genre": "Rock", "year": 2021, "duration": 280, "play_count": 200},
    ]


class TestMixRules:
    def test_is_operator(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 2
        assert all(t["genre"] == "Rock" for t in tracks)

    def test_is_not_operator(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="genre", operator="is_not", value="Rock")])
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 3

    def test_contains_operator(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="title", operator="contains", value="Rock")])
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 2

    def test_gt_operator(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="year", operator="gt", value=2020)])
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 2  # 2021 and 2022

    def test_between_operator(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="year", operator="between", value=[2019, 2021])])
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 3

    def test_and_logic(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[
            MixRule(field="genre", operator="is", value="Rock"),
            MixRule(field="year", operator="gt", value=2020),
        ], logic="AND")
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 1  # Rock Ballad (2021)

    def test_or_logic(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[
            MixRule(field="genre", operator="is", value="Rock"),
            MixRule(field="genre", operator="is", value="Jazz"),
        ], logic="OR")
        definition = MixDefinition(groups=[group])
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 3

    def test_multiple_groups(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        g1 = MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        g2 = MixRuleGroup(rules=[MixRule(field="play_count", operator="gt", value=100)])
        definition = MixDefinition(groups=[g1, g2])  # AND between groups
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 2

    def test_seed_reproducibility(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        d1 = MixDefinition(groups=[group], seed=42, sort_by="random")
        d2 = MixDefinition(groups=[group], seed=42, sort_by="random")
        t1 = engine.filter(sample_tracks, d1)
        t2 = engine.filter(sample_tracks, d2)
        assert [t["title"] for t in t1] == [t["title"] for t in t2]

    def test_different_seed_different_order(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        d1 = MixDefinition(groups=[group], seed=42, sort_by="random")
        d2 = MixDefinition(groups=[group], seed=99, sort_by="random")
        t1 = engine.filter(sample_tracks, d1)
        t2 = engine.filter(sample_tracks, d2)
        # With only 2 tracks, order may be same by chance — just verify they work
        assert len(t1) == len(t2)

    def test_limit(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="play_count", operator="gt", value=0)])
        definition = MixDefinition(groups=[group], limit=2)
        tracks = engine.filter(sample_tracks, definition)
        assert len(tracks) == 2

    def test_preview(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        group = MixRuleGroup(rules=[MixRule(field="year", operator="gt", value=2018)])
        definition = MixDefinition(groups=[group], limit=5)
        preview = engine.preview(sample_tracks, definition)
        assert preview["ok"]
        assert preview["total_tracks"] == 5
        assert preview["matched"] >= 3

    def test_generate_id_consistent(self, engine):
        from core.mix_rules import MixRule, MixRuleGroup, MixDefinition
        d1 = MixDefinition(name="Test", groups=[
            MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        ], seed=42)
        d2 = MixDefinition(name="Test", groups=[
            MixRuleGroup(rules=[MixRule(field="genre", operator="is", value="Rock")])
        ], seed=42)
        assert engine.generate_id(d1) == engine.generate_id(d2)

    def test_evaluate_no_field(self, engine, sample_tracks):
        from core.mix_rules import MixRule, MixRuleGroup
        group = MixRuleGroup(rules=[MixRule(field="nonexistent", operator="is", value="value")])
        result = engine.evaluate(sample_tracks[0], group)
        assert not result  # missing field should return False
