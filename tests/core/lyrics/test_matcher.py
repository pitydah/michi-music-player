from core.lyrics.matcher import compute_match_score, rank_candidates
from core.lyrics.models import (
    TrackIdentity, LyricsDocument, MatchConfidence, LyricsMetadata,
)


def make_candidate(title="", artist="", album="", duration_ms=0,
                   mbid="", isrc="") -> LyricsDocument:
    return LyricsDocument(
        metadata=LyricsMetadata(title=title, artist=artist, album=album),
        duration_ms=duration_ms,
        identity=TrackIdentity(
            musicbrainz_track_id=mbid, isrc=isrc,
        ),
    )


class TestMatchScore:
    def test_exact_match(self):
        identity = TrackIdentity(title="Song", artist="Artist")
        candidate = make_candidate(title="Song", artist="Artist")
        assert compute_match_score(identity, candidate) == MatchConfidence.EXACT

    def test_high_confidence(self):
        identity = TrackIdentity(title="Hello World", artist="Artist")
        candidate = make_candidate(title="Hello", artist="Artist")
        conf = compute_match_score(identity, candidate)
        assert conf in (MatchConfidence.HIGH_CONFIDENCE, MatchConfidence.EXACT)

    def test_rejected_no_match(self):
        identity = TrackIdentity(title="One Thing", artist="A")
        candidate = make_candidate(title="Something Else", artist="B")
        assert compute_match_score(identity, candidate) == MatchConfidence.REJECTED

    def test_studio_vs_live_penalty(self):
        identity = TrackIdentity(title="Song (Studio)", artist="Artist")
        candidate = make_candidate(title="Song (Live)", artist="Artist")
        conf = compute_match_score(identity, candidate)
        assert conf != MatchConfidence.EXACT

    def test_original_vs_remaster(self):
        identity = TrackIdentity(title="Original Version", artist="Artist")
        candidate = make_candidate(title="Remastered Version", artist="Artist")
        conf = compute_match_score(identity, candidate)
        assert conf != MatchConfidence.EXACT

    def test_mbid_match_boosts(self):
        identity = TrackIdentity(title="Song", musicbrainz_track_id="mbid-1")
        candidate = make_candidate(title="Song", mbid="mbid-1")
        assert compute_match_score(identity, candidate) == MatchConfidence.EXACT

    def test_isrc_match(self):
        identity = TrackIdentity(title="Song", artist="Artist", isrc="USABC1234567")
        candidate = make_candidate(title="Song", artist="Artist", isrc="USABC1234567")
        assert compute_match_score(identity, candidate) in (MatchConfidence.HIGH_CONFIDENCE, MatchConfidence.EXACT)

    def test_duration_mismatch_penalty(self):
        identity = TrackIdentity(title="Song", artist="Artist", duration_ms=240000)
        candidate = make_candidate(title="Song", artist="Artist", duration_ms=120000)
        conf = compute_match_score(identity, candidate)
        assert conf != MatchConfidence.EXACT

    def test_duration_close(self):
        identity = TrackIdentity(title="Song", artist="Artist", duration_ms=240000)
        candidate = make_candidate(title="Song", artist="Artist", duration_ms=242000)
        assert compute_match_score(identity, candidate) == MatchConfidence.EXACT

    def test_ambigous_match(self):
        identity = TrackIdentity(title="Common Name", artist="Artist A")
        candidate = make_candidate(title="Common Name", artist="Artist B")
        conf = compute_match_score(identity, candidate)
        assert conf == MatchConfidence.AMBIGUOUS

    def test_same_title_different_artists_low(self):
        identity = TrackIdentity(title="Popular Song", artist="Artist One")
        candidate = make_candidate(title="Popular Song", artist="Artist Two")
        conf = compute_match_score(identity, candidate)
        assert conf != MatchConfidence.EXACT


class TestRankCandidates:
    def test_returns_sorted_by_confidence(self):
        identity = TrackIdentity(title="Song", artist="Artist")
        candidates = [
            make_candidate(title="Song", artist="Artist"),
            make_candidate(title="Wrong", artist="Wrong"),
        ]
        ranked = rank_candidates(identity, candidates)
        assert len(ranked) >= 1
        assert ranked[0][1] == MatchConfidence.EXACT

    def test_removes_rejected(self):
        identity = TrackIdentity(title="Song", artist="Artist")
        candidates = [
            make_candidate(title="Totally Different", artist="Unknown"),
        ]
        ranked = rank_candidates(identity, candidates)
        assert len(ranked) == 0

    def test_feat_handling(self):
        identity = TrackIdentity(title="Song", artist="Main Artist feat. Guest")
        candidate = make_candidate(title="Song", artist="Main Artist feat. Guest")
        conf = compute_match_score(identity, candidate)
        assert conf in (MatchConfidence.HIGH_CONFIDENCE, MatchConfidence.EXACT)

    def test_radio_edit_vs_album(self):
        identity = TrackIdentity(title="Song (Radio Edit)", artist="Artist")
        candidate = make_candidate(title="Song", artist="Artist")
        conf = compute_match_score(identity, candidate)
        assert conf != MatchConfidence.REJECTED
