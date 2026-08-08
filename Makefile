.PHONY: test test-full test-advisory lint compile wheel clean

# Fast blocking path — matches the CI unit job selection exactly
# (same ignores: qml/large_library/perf, same -k filter, same deselect).
test:
	QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300 \
		--ignore=tests/qml --ignore=tests/test_large_library.py \
		--ignore=tests/perf -k "not qt_widget and not QtWidget" \
		--deselect tests/test_context_semantic_audit.py::TestContextSemanticAudit::test_no_appevent_import_outside_context

# Full inventory — diagnostic full suite (non-blocking by default).
test-full:
	./scripts/ci_canonical.sh --full

# Advisory development/quarantine with failures surfaced as exit code.
test-advisory:
	./scripts/ci_canonical.sh --strict-advisory

lint:
	ruff check .

compile:
	python -m compileall -q -x '.venv/|\.tmpl\.' .

wheel:
	python -m build --wheel

clean:
	rm -rf dist/ build/ *.egg-info __pycache__ .venv
