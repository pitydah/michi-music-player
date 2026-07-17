.PHONY: test lint compile wheel clean

test:
	QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --ignore=tests/qml --ignore=tests/test_large_library.py --timeout=300

lint:
	ruff check .

compile:
	python -m compileall -q -x '.venv/|\.tmpl\.' .

wheel:
	python -m build --wheel

clean:
	rm -rf dist/ build/ *.egg-info __pycache__ .venv
