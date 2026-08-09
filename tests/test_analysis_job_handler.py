"""Handler contracts for make_analysis_handler (M1.1 — productive review correction).

Tests validate the real productive contract:
- Port normalises AudioAnalysisService statuses into ``ok`` boolean.
- Handler checks ``ok``, never a hard-coded status string.
- Payload is minimally validated.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from core.worker_manager import CancellationToken, CancelledError


def _make_fake_ctx(token=None):
    ctx = MagicMock()
    ctx.token = token or CancellationToken()
    ctx.report_progress = MagicMock()
    ctx.task_id = "job_test"
    return ctx


def _make_fake_job(filepath="/tracks/foo.flac"):
    job = MagicMock()
    job.payload = {"request": {"filepath": filepath}}
    job.type = "analysis"
    job.owner = "audio_lab"
    return job


# ── Port normalisation (status → ok) ──


def test_analysis_port_normalizes_completed_to_ok():
    """_AnalysisPort maps 'completed' → ok=True."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "completed",
        "features": {"bpm": 120},
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result.get("ok") is True
    assert result["status"] == "completed"
    assert result["features"]["bpm"] == 120


def test_analysis_port_normalizes_error_to_not_ok():
    """_AnalysisPort maps 'error' → ok=False."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "error",
        "error": "Unsupported codec",
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result.get("ok") is False
    assert result["status"] == "error"


def test_analysis_port_normalizes_unsupported_to_not_ok():
    """_AnalysisPort maps 'unsupported' → ok=False."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "unsupported",
        "explanation": "No backend",
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result.get("ok") is False
    assert result["status"] == "unsupported"


def test_analysis_port_normalizes_disabled_to_not_ok():
    """_AnalysisPort maps 'disabled' → ok=False."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "disabled",
        "error": "Análisis desactivado.",
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result.get("ok") is False
    assert result["status"] == "disabled"


def test_analysis_port_normalizes_unknown_to_not_ok():
    """_AnalysisPort maps 'unknown' → ok=False."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "unknown",
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result.get("ok") is False


def test_analysis_port_preserves_original_status():
    """_AnalysisPort keeps the original status for UI readback."""
    from core.composition.jobs import _AnalysisPort

    analysis = MagicMock()
    analysis.analyze_file.return_value = {
        "status": "completed",
        "features": {"bpm": 120},
    }
    port = _AnalysisPort(analysis)
    result = port.analyze("/tracks/foo.flac")

    assert result["status"] == "completed"  # preserved
    assert result.get("ok") is True         # normalised


# ── Handler: productive completed → SUCCEEDED ──


def test_handler_succeeds_on_port_ok_true():
    """Handler returns the result when port.analyze returns ok=True."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": True, "status": "completed", "features": {"bpm": 120},
    }
    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    result = handler(job, ctx)

    port.analyze.assert_called_once_with("/tracks/foo.flac", ctx)
    ctx.report_progress.assert_any_call(0.1, "Starting analysis")
    ctx.report_progress.assert_any_call(1.0, "Analysis complete")
    assert result["ok"] is True
    assert result["status"] == "completed"


# ── Handler: error / unsupported / disabled → FAILED ──


def test_handler_raises_on_port_ok_false_error():
    """Handler raises RuntimeError when port returns ok=False (error)."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": False, "status": "error", "error": "Unsupported codec",
    }
    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="Unsupported codec"):
        handler(job, ctx)


def test_handler_raises_on_port_ok_false_unsupported():
    """Handler raises RuntimeError when port returns ok=False (unsupported)."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": False, "status": "unsupported", "error": "No backend",
    }
    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="No backend"):
        handler(job, ctx)


def test_handler_raises_on_port_ok_false_disabled():
    """Handler raises RuntimeError when port returns ok=False (disabled)."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": False, "status": "disabled", "error": "Analysis disabled",
    }
    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="Analysis disabled"):
        handler(job, ctx)


def test_handler_never_reports_complete_on_failure():
    """Progress 1.0 is NEVER reported when the result is rejected.

    The handler must validate the result BEFORE emitting the final
    progress report.  A failed analysis must never show as 100 %
    complete.
    """
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": False, "status": "error", "error": "Backend crash",
    }
    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="Backend crash"):
        handler(job, ctx)

    # progress 1.0 / "Analysis complete" must never have been emitted
    progress_calls = [
        args for args, _ in ctx.report_progress.call_args_list
    ]
    for fraction, message in progress_calls:
        assert fraction < 1.0 or "Complete" not in str(message), (
            f"Progress should never reach 100 % with 'complete' message "
            f"on failure. Got: {fraction:.2f} / {message}"
        )


# ── Handler: port is None ──


def test_handler_raises_when_port_is_none():
    """Handler raises RuntimeError('AudioLabService unavailable') when port is None."""
    from core.jobs.handlers import make_analysis_handler

    handler = make_analysis_handler(None)
    job = _make_fake_job()
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="AudioLabService unavailable"):
        handler(job, ctx)


# ── Payload validation ──


def test_handler_rejects_missing_request():
    """Handler raises when payload has no 'request' key."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    handler = make_analysis_handler(port)
    job = MagicMock()
    job.payload = {}
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="INVALID_PAYLOAD"):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_rejects_none_request():
    """Handler raises when request is None."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    handler = make_analysis_handler(port)
    job = MagicMock()
    job.payload = {"request": None}
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="INVALID_PAYLOAD"):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_rejects_missing_filepath():
    """Handler raises when filepath is missing from request."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    handler = make_analysis_handler(port)
    job = MagicMock()
    job.payload = {"request": {}}
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="INVALID_PAYLOAD"):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_rejects_empty_filepath():
    """Handler raises when filepath is an empty string."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    handler = make_analysis_handler(port)
    job = _make_fake_job(filepath="")
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="INVALID_PAYLOAD"):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_rejects_non_string_filepath():
    """Handler raises when filepath is not a string."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    handler = make_analysis_handler(port)
    job = MagicMock()
    job.payload = {"request": {"filepath": 12345}}
    ctx = _make_fake_ctx()

    with pytest.raises(RuntimeError, match="INVALID_PAYLOAD"):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_strips_filepath():
    """Handler strips whitespace from filepath before passing to port."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {
        "ok": True, "status": "completed", "features": {},
    }
    handler = make_analysis_handler(port)
    job = MagicMock()
    job.payload = {"request": {"filepath": "  /tracks/foo.flac  "}}
    ctx = _make_fake_ctx()

    handler(job, ctx)
    port.analyze.assert_called_once_with("/tracks/foo.flac", ctx)


# ── Cancellation ──


def test_handler_observes_cancellation_before_port_call():
    """Handler raises CancelledError when token is cancelled before the port call."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    token = CancellationToken()

    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx(token=token)

    token.request_cancel()

    with pytest.raises(CancelledError):
        handler(job, ctx)

    port.analyze.assert_not_called()


def test_handler_observes_cancellation_after_port_call():
    """Handler raises CancelledError after port.analyze returns but token is cancelled."""
    from core.jobs.handlers import make_analysis_handler

    port = MagicMock()
    port.analyze.return_value = {"ok": True, "status": "completed"}
    token = CancellationToken()

    handler = make_analysis_handler(port)
    job = _make_fake_job()
    ctx = _make_fake_ctx(token=token)

    def cancel_after_call(_filepath, _ctx):
        token.request_cancel()
        return {"ok": True, "status": "completed"}

    port.analyze.side_effect = cancel_after_call

    with pytest.raises(CancelledError):
        handler(job, ctx)

    port.analyze.assert_called_once()
