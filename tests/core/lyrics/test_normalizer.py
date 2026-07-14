from core.lyrics.normalizer import TrackIdentityNormalizer
from core.lyrics.models import TrackIdentity


class TestTrackIdentityNormalizer:
    def test_normalize_basic(self):
        identity = TrackIdentity(title="Hello World", artist="Test Artist")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "hello" in norm.normalized_title
        assert "world" in norm.normalized_title

    def test_normalize_feat(self):
        identity = TrackIdentity(title="Song feat. Artist", artist="Main Artist")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "feat" not in norm.normalized_title

    def test_normalize_ft(self):
        identity = TrackIdentity(title="Song ft. Guest")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "ft" not in norm.normalized_title

    def test_normalize_live(self):
        identity = TrackIdentity(title="Song (Live)")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "live" not in norm.normalized_title

    def test_normalize_remaster(self):
        identity = TrackIdentity(title="Song (Remastered)")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "remastered" not in norm.normalized_title

    def test_normalize_unicode(self):
        identity = TrackIdentity(title="Café")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "café" in norm.normalized_title

    def test_normalize_punctuation(self):
        identity = TrackIdentity(title="Hello, World!")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert norm.normalized_title == "hello world"

    def test_are_similar_exact(self):
        assert TrackIdentityNormalizer.are_similar("Hello World", "Hello World")

    def test_are_similar_case(self):
        assert TrackIdentityNormalizer.are_similar("hello world", "HELLO WORLD")

    def test_are_similar_substring(self):
        assert TrackIdentityNormalizer.are_similar("Hello", "Hello World")

    def test_are_similar_different(self):
        assert not TrackIdentityNormalizer.are_similar("Hello", "Goodbye")

    def test_matching_tokens(self):
        identity = TrackIdentity(title="Hello World", artist="Test Artist")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "hello" in norm.matching_tokens
        assert "world" in norm.matching_tokens

    def test_is_live_version(self):
        assert TrackIdentityNormalizer.is_live_version("Song (Live)")
        assert TrackIdentityNormalizer.is_live_version("Song - En Vivo")
        assert not TrackIdentityNormalizer.is_live_version("Song (Studio)")

    def test_is_remix(self):
        assert TrackIdentityNormalizer.is_remix("Song (Remix)")
        assert TrackIdentityNormalizer.is_remix("Song (Remix)")
        assert not TrackIdentityNormalizer.is_remix("Song (Original)")

    def test_normalize_removes_brackets(self):
        identity = TrackIdentity(title="Song [Bonus Track]")
        norm = TrackIdentityNormalizer.normalize(identity)
        assert "bonus" not in norm.normalized_title
