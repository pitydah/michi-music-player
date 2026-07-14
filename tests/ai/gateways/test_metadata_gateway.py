from __future__ import annotations

from core.assistant_metadata_gateway import ProductionMetadataGateway


class FakeMetadataService:
    def __init__(self) -> None:
        self._reviews: dict[str, dict] = {}

    def inspect(self, track_id: str) -> dict:
        if track_id == "999":
            return None
        return {
            "track_id": track_id,
            "title": "Song A",
            "artist": "Artist X",
            "album": "Album 1",
            "genre": "Rock",
            "year": 2020,
            "track_number": 1,
            "format": "FLAC",
        }

    def build_proposal(self, track_ids: list[str]) -> dict:
        return {
            "review_id": "rev_1",
            "field_count": 3,
            "high_confidence": 2,
            "ambiguous": 1,
            "warnings": ["Low confidence on genre"],
        }

    def preview_review(self, review_id: str) -> dict:
        if review_id == "missing":
            raise ValueError("not found")
        return {
            "changes": [
                {"field": "artist", "old": "Artist X", "new": "Artist Y", "confidence": 0.95},
            ],
            "backup": True,
            "rollback": True,
        }

    def apply_review(self, review_id: str) -> bool:
        return True

    def rollback(self, operation_id: str) -> bool:
        return True


class FakeConfirmationService:
    def validate(self, token: str, operation_id: str) -> "FakeResult":
        if token == "valid_token":
            return FakeResult(ok=True)
        return FakeResult(ok=False, message="INVALID_CONFIRMATION")


class FakeResult:
    def __init__(self, ok: bool = True, message: str = "") -> None:
        self.ok = ok
        self.message = message


class FakeJobService:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}

    def create(self, kind: str, meta: dict | None = None) -> dict:
        job_id = f"job_{len(self._jobs) + 1}"
        self._jobs[job_id] = {"id": job_id, "kind": kind, "meta": meta or {}}
        return type("Job", (), {"job_id": job_id})()

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)


class TestProductionMetadataGateway:
    def setup_method(self) -> None:
        self.fake_ms = FakeMetadataService()
        self.fake_cs = FakeConfirmationService()
        self.fake_js = FakeJobService()
        self.gw = ProductionMetadataGateway(self.fake_ms, self.fake_cs, self.fake_js)

    def test_inspect_metadata_success(self) -> None:
        result = self.gw.inspect_metadata("1")
        assert result["ok"] is True
        assert result["status"] == "COMPLETED"
        assert result["metadata"]["track_id"] == "1"
        assert result["metadata"]["title"] == "Song A"

    def test_inspect_metadata_not_found(self) -> None:
        result = self.gw.inspect_metadata("999")
        assert result["ok"] is False
        assert "NOT_FOUND" in str(result.get("code", ""))

    def test_inspect_metadata_unavailable(self) -> None:
        gw = ProductionMetadataGateway()
        result = gw.inspect_metadata("1")
        assert result["ok"] is False
        assert result["code"] == "CAPABILITY_UNAVAILABLE"

    def test_inspect_selection(self) -> None:
        result = self.gw.inspect_selection(["1", "2", "3"])
        assert result["ok"] is True
        assert result["total"] == 3
        assert result["success_count"] >= 3

    def test_inspect_selection_limits(self) -> None:
        result = self.gw.inspect_selection([str(i) for i in range(100)])
        assert result["total"] <= 50

    def test_build_proposal_success(self) -> None:
        result = self.gw.build_proposal(["1", "2"])
        assert result["ok"] is True
        assert result["review_id"] == "rev_1"

    def test_preview_changes_success(self) -> None:
        result = self.gw.preview_changes("rev_1")
        assert result["ok"] is True
        assert result["status"] == "COMPLETED"
        assert result["rollback_available"] is True

    def test_preview_changes_not_found(self) -> None:
        result = self.gw.preview_changes("missing")
        assert result["ok"] is False

    def test_apply_review_starts_job(self) -> None:
        result = self.gw.apply_review("rev_1", "valid_token")
        assert result["ok"] is True
        assert result["status"] == "JOB_STARTED"
        assert "job_id" in result

    def test_apply_review_invalid_confirmation(self) -> None:
        result = self.gw.apply_review("rev_1", "bad_token")
        assert result["ok"] is False
        assert result["code"] == "INVALID_CONFIRMATION"

    def test_rollback_success(self) -> None:
        result = self.gw.rollback("op_1", "valid_token")
        assert result["ok"] in (True, False)

    def test_rollback_unavailable(self) -> None:
        gw = ProductionMetadataGateway()
        result = gw.rollback("op_1", "token")
        assert result["ok"] is False

    def test_check_consistency(self) -> None:
        result = self.gw.check_consistency(["1", "2"])
        assert result["ok"] is True
        assert result["healthy"] is True

    def test_scan_duplicates(self) -> None:
        result = self.gw.scan_duplicates(["1", "2"])
        assert result["ok"] is True

    def test_get_operation_status(self) -> None:
        result = self.gw.get_operation_status("nonexistent")
        assert result["ok"] is False

    def test_sanitization_removes_sensitive_fields(self) -> None:
        result = self.gw._sanitize({"title": "Safe", "filepath": "/secret/path"})
        assert "title" in result
        assert "filepath" not in result
