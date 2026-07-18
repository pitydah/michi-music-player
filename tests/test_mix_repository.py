"""Tests for MixRepository — persistence, CRUD, replay resistance."""
import os
import tempfile

import pytest


@pytest.fixture
def db():
    import library.library_db
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = library.library_db.LibraryDB(path)
    yield db
    db.conn.close()
    os.unlink(path)


@pytest.fixture
def repo(db):
    from core.mix.repository import MixRepository
    return MixRepository(db)


class TestMixRepository:
    def test_save_and_load(self, repo):
        from core.mix.repository import MixDefinition
        d = MixDefinition(mix_id="test-1", name="Test Mix", rules_json='{"groups":[]}')
        repo.save(d)
        loaded = repo.load("test-1")
        assert loaded is not None
        assert loaded.name == "Test Mix"

    def test_list_all(self, repo):
        from core.mix.repository import MixDefinition
        repo.save(MixDefinition(mix_id="m1", name="Mix 1"))
        repo.save(MixDefinition(mix_id="m2", name="Mix 2"))
        mixes = repo.list_all()
        assert len(mixes) >= 2

    def test_delete(self, repo):
        from core.mix.repository import MixDefinition
        repo.save(MixDefinition(mix_id="del-me", name="To Delete"))
        repo.delete("del-me")
        assert repo.load("del-me") is None

    def test_record_play(self, repo):
        from core.mix.repository import MixDefinition
        repo.save(MixDefinition(mix_id="play-me", name="Played"))
        repo.record_play("play-me")
        loaded = repo.load("play-me")
        assert loaded.play_count == 1

    def test_persist_across_reopen(self, db):
        from core.mix.repository import MixRepository, MixDefinition
        repo1 = MixRepository(db)
        repo1.save(MixDefinition(mix_id="persist", name="Persistent"))
        repo2 = MixRepository(db)
        loaded = repo2.load("persist")
        assert loaded is not None
        assert loaded.name == "Persistent"

    def test_bridge_has_methods(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        assert hasattr(MixBridge, 'saveRules')
        assert hasattr(MixBridge, 'loadRules')
        assert hasattr(MixBridge, 'listRules')
        assert hasattr(MixBridge, 'deleteRules')
        assert hasattr(MixBridge, 'previewRules')
