from __future__ import annotations

import pytest

from michi_ai.intent_classifier import classify
from michi_ai.recommender import recommend
from michi_ai.response_composer import compose
from michi_ai.engine import process


class TestClassify:
    def test_classify_play_music_jazz(self):
        assert classify("pon jazz") == "play_music"

    def test_classify_play_music_rock(self):
        assert classify("reproduce rock") == "play_music"

    def test_classify_play_music_generic(self):
        assert classify("reproduce algo de música") == "play_music"

    def test_classify_play_music_english(self):
        assert classify("play some music") == "play_music"

    def test_classify_recommend(self):
        assert classify("recomienda algo") == "recommend"

    def test_classify_recommend_suggest(self):
        assert classify("sugiere música") == "recommend"

    def test_classify_recommend_english(self):
        assert classify("what do you recommend") == "recommend"

    def test_classify_artist_info_who_is(self):
        assert classify("quién es Pink Floyd") == "artist_info"

    def test_classify_artist_info_tell_me(self):
        assert classify("cuéntame sobre Queen") == "artist_info"

    def test_classify_artist_info_english(self):
        assert classify("tell me about Miles Davis") == "artist_info"

    def test_classify_album_info(self):
        assert classify("dime del álbum The Dark Side") == "album_info"

    def test_classify_genre_info(self):
        assert classify("qué es el género rock") == "genre_info"

    def test_classify_library_status(self):
        assert classify("cuántas canciones tengo") == "library_status"

    def test_classify_greeting_hola(self):
        assert classify("hola") == "greeting"

    def test_classify_greeting_buenos_dias(self):
        assert classify("buenos días") == "greeting"

    def test_classify_greeting_hello(self):
        assert classify("hello") == "greeting"

    def test_classify_unknown_nonsense(self):
        assert classify("xyzzy flurbo garblex") == "unknown"

    def test_classify_unknown_empty(self):
        assert classify("") == "unknown"


class TestRecommender:
    def test_recommend_by_genre(self):
        results = recommend(genre="jazz")
        assert len(results) >= 2
        assert all(t["genre"] == "jazz" for t in results)

    def test_recommend_by_artist(self):
        results = recommend(artist="Pink Floyd")
        assert all("Pink Floyd" in t["artist"] for t in results)
        assert len(results) >= 2

    def test_recommend_empty_genre(self):
        results = recommend(genre="nonexistent")
        assert results == []

    def test_recommend_default_count(self):
        results = recommend()
        assert len(results) == 5

    def test_recommend_custom_count(self):
        results = recommend(count=3)
        assert len(results) == 3

    def test_recommend_returns_valid_structure(self):
        results = recommend(count=1)
        assert len(results) == 1
        item = results[0]
        assert "artist" in item
        assert "album" in item
        assert "title" in item
        assert "genre" in item

    def test_recommend_by_mood_happy(self):
        results = recommend(mood="feliz")
        assert len(results) >= 1


class TestResponseComposer:
    def test_composer_play(self):
        result = compose("play_music", {"items": [{"title": "Money", "artist": "Pink Floyd", "genre": "rock"}]})
        assert "Money" in result
        assert "Pink Floyd" in result

    def test_composer_play_no_items(self):
        result = compose("play_music", {"items": []})
        assert "No encontré" in result

    def test_composer_recommend(self):
        result = compose("recommend", {"items": [{"title": "So What", "artist": "Miles Davis", "genre": "jazz"}]})
        assert "So What" in result
        assert "Miles Davis" in result

    def test_composer_recommend_empty(self):
        result = compose("recommend", {"items": []})
        assert "No tengo recomendaciones" in result

    def test_composer_greeting(self):
        result = compose("greeting")
        assert "Michi AI" in result

    def test_composer_artist_info(self):
        result = compose("artist_info", {"artist": "Pink Floyd", "examples": "Money, Time"})
        assert "Pink Floyd" in result
        assert "Money" in result

    def test_composer_album_info(self):
        result = compose("album_info", {"album": "Dark Side", "artist": "Pink Floyd", "examples": "Money"})
        assert "Dark Side" in result

    def test_composer_library_status(self):
        result = compose("library_status", {"tracks": 20, "albums": 10, "artists": 5})
        assert "20" in result
        assert "10" in result
        assert "5" in result

    def test_composer_unknown(self):
        result = compose("unknown")
        assert "No entendí" in result


class TestEngine:
    def test_engine_process_play_music(self):
        result = process("reproduce jazz")
        assert result["intent"] == "play_music"
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        assert isinstance(result["actions"], list)

    def test_engine_process_recommend(self):
        result = process("recomienda algo")
        assert result["intent"] == "recommend"
        assert len(result["response"]) > 0

    def test_engine_process_artist_info(self):
        result = process("quién es Pink Floyd")
        assert result["intent"] == "artist_info"
        assert "Pink Floyd" in result["response"]

    def test_engine_process_greeting(self):
        result = process("hola")
        assert result["intent"] == "greeting"
        assert "Michi AI" in result["response"]

    def test_engine_process_unknown(self):
        result = process("xyzzy flurbo garblex")
        assert result["intent"] == "unknown"
        assert "No entendí" in result["response"]

    def test_engine_process_empty(self):
        result = process("")
        assert result["intent"] == "unknown"
        assert "escribe algo" in result["response"]

    def test_engine_process_library_status(self):
        result = process("cuántas canciones tengo")
        assert result["intent"] == "library_status"
        assert any(w in result["response"] for w in ["canciones", "temas", "discos"])
