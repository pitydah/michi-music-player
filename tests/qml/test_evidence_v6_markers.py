"""Tests for QML Evidence V8: marker parsing, JUnit matching, scores."""
import ast
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"
CONFIG_FILE = REPO / "config" / "qml_modules.yaml"

V8_MARKERS = {"qml_module", "qml_dimension", "qml_route", "qml_workflow", "widget_replacement"}

SCORE_MAP = {
    "PASSED": 1.0,
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE_DECLARED": 1.0,
    "DEFERRED_PHYSICAL": 1.0,
}

KNOWN_DIMENSIONS = []


def _extract_marker_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.attr in V8_MARKERS:
        return node.attr
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in V8_MARKERS:
        return node.func.attr
    return None


pytestmark = [pytest.mark.qml_module("evidence"), pytest.mark.qml_dimension("verification")]


def _get_call_arg(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    for kw in node.keywords:
        if kw.arg in ("module", "dimension", "route", "workflow", "widget") and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _get_enclosing_class(tree: ast.Module, func_node: ast.FunctionDef) -> str | None:
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and func_node in node.body:
            return node.name
    return None


def find_marked_tests(repo: Path) -> list[dict]:
    results = []
    testdir = repo / "tests/qml"
    if not testdir.exists():
        return results
    for pyfile in sorted(testdir.rglob("test_*.py")):
        text = pyfile.read_text()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        module_markers = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                name = _extract_marker_name(elt)
                                if name:
                                    module_markers[name] = _get_call_arg(elt) if isinstance(elt, ast.Call) and _get_call_arg(elt) else name
                        elif isinstance(node.value, ast.Call):
                            name = _extract_marker_name(node.value)
                            if name:
                                module_markers[name] = _get_call_arg(node.value) if _get_call_arg(node.value) else name
                        elif isinstance(node.value, ast.Attribute):
                            name = _extract_marker_name(node.value)
                            if name:
                                module_markers[name] = name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                markers = dict(module_markers)
                for deco in node.decorator_list:
                    name = _extract_marker_name(deco)
                    if name:
                        arg = _get_call_arg(deco) if isinstance(deco, ast.Call) else name
                        markers[name] = arg or name
                if not markers:
                    continue
                cls_node = _get_enclosing_class(tree, node)
                relpath = str(pyfile.relative_to(repo))
                entry = {
                    "nodeid": f"{relpath}::{node.name}" if not cls_node else f"{relpath}::{cls_node}::{node.name}",
                    "module": markers.get("qml_module", ""),
                    "dimension": markers.get("qml_dimension", ""),
                    "route": markers.get("qml_route", ""),
                    "workflow": markers.get("qml_workflow", ""),
                    "widget": markers.get("widget_replacement", ""),
                    "file": relpath,
                    "class": cls_node or "",
                    "function": node.name,
                }
                results.append(entry)
    return results


def parse_junit(junit_path: Path) -> list[dict]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    testcases = []
    for ts in root:
        suite_name = ts.get("name", "")
        for tc in ts:
            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            testcases.append({
                "name": name,
                "classname": classname,
                "nodeid": f"{classname}::{name}" if classname else name,
                "time": float(tc.get("time", 0)),
                "failure": failure_el.text if failure_el is not None else error_el.text if error_el is not None else None,
                "skipped": skipped_el is not None,
                "suite": suite_name,
            })
    return testcases


def build_dimension_status(dim, module_name, testcases, marked_tests, weight):
    dim_tests = []
    for mt in marked_tests:
        if mt.get("dimension") != dim:
            continue
        if mt.get("module") != module_name:
            continue
        matched = False
        mt_nodeid = mt.get("nodeid", "")
        for tc in testcases:
            tc_nodeid = tc.get("nodeid", "")
            if tc_nodeid == mt_nodeid:
                dim_tests.append(tc)
                matched = True
                break
            combined = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            if combined == mt_nodeid:
                dim_tests.append(tc)
                matched = True
                break
        if not matched:
            dim_tests.append({
                "name": mt.get("function", ""),
                "classname": mt.get("file", ""),
                "nodeid": mt_nodeid,
                "time": 0,
                "failure": None,
                "skipped": False,
                "suite": "",
                "_unmatched": True,
            })
    if not dim_tests:
        return {"status": "NOT_APPLICABLE", "tests": [], "weight": weight, "reason": ""}
    failures = [t for t in dim_tests if t.get("failure")]
    skips = [t for t in dim_tests if t.get("skipped") and not t.get("failure")]
    passed = [t for t in dim_tests if not t.get("failure") and not t.get("skipped") and not t.get("_unmatched")]
    if failures:
        return {"status": "FAILED", "tests": dim_tests, "weight": weight, "reason": f"{len(failures)} test(s) failed"}
    if any(t.get("_unmatched") for t in dim_tests):
        return {"status": "MISSING", "tests": dim_tests, "weight": weight, "reason": "No JUnit evidence for marked test"}
    if skips and not passed:
        return {"status": "MISSING", "tests": dim_tests, "weight": weight, "reason": "All tests skipped without reason"}
    return {"status": "PASSED", "tests": dim_tests, "weight": weight, "reason": ""}


def derive_composite_status(dimensions):
    statuses = {d: v["status"] for d, v in dimensions.items()}

    def _all_pass(*names):
        return all(statuses.get(n) == "PASSED" for n in names)

    compiles = _all_pass("route_load", "qml_instance")
    read_only = compiles and _all_pass("model_data", "service_wiring", "read")
    partial = read_only and any(
        statuses.get(d) == "PASSED" for d in ["primary_action", "secondary_actions", "write"]
    )
    productive_basic = _all_pass("primary_action", "error_contract", "integration", "vertical_workflow")
    persistence_ok = statuses.get("persistence") in ("PASSED", "NOT_APPLICABLE")
    async_ok = statuses.get("async_execution") in ("PASSED", "NOT_APPLICABLE")
    cancel_ok = statuses.get("real_cancellation") in ("PASSED", "NOT_APPLICABLE")
    productive = productive_basic and persistence_ok and async_ok and cancel_ok
    all_applicable = all(
        v["status"] in ("PASSED", "NOT_APPLICABLE") for v in dimensions.values()
    )
    parity = productive and all_applicable
    if parity:
        return "PARITY"
    if productive:
        return "PRODUCTIVE"
    if partial:
        return "PARTIAL_WORKFLOW"
    if read_only:
        return "READ_ONLY"
    if compiles:
        return "COMPILES"
    if any(v["status"] == "PASSED" for v in dimensions.values()):
        return "SCAFFOLDED"
    return "NOT_IMPLEMENTED"


def compute_module_score(dimensions):
    total_weight = 0
    weighted_sum = 0.0
    for dim_val in dimensions.values():
        weight = dim_val.get("weight", 0)
        status = dim_val.get("status", "NOT_APPLICABLE")
        factor = SCORE_MAP.get(status, 0.0)
        weighted_sum += weight * factor
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return (weighted_sum / total_weight) * 100.0


@pytest.fixture
def config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


class TestMarkerParsing:
    @staticmethod
    def _write_test(tmp_path, name, content):
        qmldir = tmp_path / "tests" / "qml"
        qmldir.mkdir(parents=True, exist_ok=True)
        pyfile = qmldir / name
        pyfile.write_text(content)
        return pyfile

    def test_extract_function_level_marker(self, tmp_path):
        self._write_test(tmp_path, "test_foo.py", "import pytest\n\ndef test_bar():\n    pass\n")
        text = (tmp_path / "tests" / "qml" / "test_foo.py").read_text()
        tree = ast.parse(text)
        funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert len(funcs) == 1

    def test_function_level_qml_module(self, tmp_path):
        self._write_test(tmp_path, "test_mod.py",
            "import pytest\n"
            "@pytest.mark.qml_module(\"library\")\n"
            "@pytest.mark.qml_dimension(\"read\")\n"
            "def test_read_something():\n"
            "    pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 1
        assert results[0]["module"] == "library"
        assert results[0]["dimension"] == "read"
        assert results[0]["function"] == "test_read_something"

    def test_class_level_markers(self, tmp_path):
        self._write_test(tmp_path, "test_class.py",
            "import pytest\n"
            "class TestSuite:\n"
            "    @pytest.mark.qml_module(\"playback\")\n"
            "    @pytest.mark.qml_dimension(\"primary_action\")\n"
            "    def test_play(self):\n"
            "        pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 1
        assert results[0]["module"] == "playback"
        assert results[0]["dimension"] == "primary_action"
        assert results[0]["function"] == "test_play"

    def test_module_level_pytestmark_list(self, tmp_path):
        self._write_test(tmp_path, "test_module.py",
            "import pytest\n"
            "pytestmark = [pytest.mark.qml_module(\"workflows\"), pytest.mark.qml_dimension(\"vertical_workflow\")]\n"
            "def test_vertical():\n"
            "    pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 1
        assert results[0]["module"] == "workflows"
        assert results[0]["dimension"] == "vertical_workflow"

    def test_module_level_pytestmark_single(self, tmp_path):
        self._write_test(tmp_path, "test_single.py",
            "import pytest\n"
            "pytestmark = pytest.mark.qml_module(\"settings\")\n"
            "def test_setting():\n"
            "    pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 1
        assert results[0]["module"] == "settings"

    def test_nodeid_format(self, tmp_path):
        self._write_test(tmp_path, "test_nodeid.py",
            "import pytest\n"
            "@pytest.mark.qml_module(\"mix\")\n"
            "@pytest.mark.qml_dimension(\"async_execution\")\n"
            "def test_mix_async():\n"
            "    pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 1
        assert "test_nodeid.py" in results[0]["nodeid"]
        assert "test_mix_async" in results[0]["nodeid"]

    def test_multiple_tests_same_module_different_dimensions(self, tmp_path):
        self._write_test(tmp_path, "test_multiple.py",
            "import pytest\n"
            "pytestmark = [pytest.mark.qml_module(\"library\")]\n\n"
            "@pytest.mark.qml_dimension(\"read\")\n"
            "def test_read():\n"
            "    pass\n\n"
            "@pytest.mark.qml_dimension(\"write\")\n"
            "def test_write():\n"
            "    pass\n"
        )
        results = find_marked_tests(tmp_path)
        assert len(results) == 2
        dims = {r["dimension"] for r in results}
        assert dims == {"read", "write"}

    def test_no_markers_returns_empty(self, tmp_path):
        self._write_test(tmp_path, "test_unmarked.py", "def test_unmarked():\n    pass\n")
        results = find_marked_tests(tmp_path)
        assert len(results) == 0

    def test_syntax_error_skipped(self, tmp_path):
        self._write_test(tmp_path, "test_broken.py", "def test_broken(:\n    pass\n")
        results = find_marked_tests(tmp_path)
        assert len(results) == 0


class TestJunitMatching:
    def test_exact_nodeid_matching(self):
        tc = {"name": "test_play", "classname": "tests/qml/test_foo.py::TestSuite", "nodeid": "tests/qml/test_foo.py::TestSuite::test_play"}
        assert tc["nodeid"] == f"{tc['classname']}::{tc['name']}"

    def test_junit_parse_basic(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0">
    <testcase classname="test_foo" name="test_bar" time="0.1" />
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results.xml"
        jfile.write_text(xml_content)
        testcases = parse_junit(jfile)
        assert len(testcases) == 1
        assert testcases[0]["nodeid"] == "test_foo::test_bar"

    def test_junit_with_failure(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1">
    <testcase classname="test_foo" name="test_fail" time="0.1">
      <failure message="AssertionError">assert 0</failure>
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results_fail.xml"
        jfile.write_text(xml_content)
        testcases = parse_junit(jfile)
        assert len(testcases) == 1
        assert testcases[0]["failure"] is not None

    def test_junit_with_skip(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" skipped="1">
    <testcase classname="test_foo" name="test_skip" time="0.0">
      <skipped message="unconditional" type="pytest.skip" />
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results_skip.xml"
        jfile.write_text(xml_content)
        testcases = parse_junit(jfile)
        assert len(testcases) == 1
        assert testcases[0]["skipped"] is True

    def test_marked_test_matches_junit(self, tmp_path):
        qmldir = tmp_path / "tests" / "qml"
        qmldir.mkdir(parents=True, exist_ok=True)
        pyfile = qmldir / "test_matched.py"
        pyfile.write_text(
            "import pytest\n"
            "@pytest.mark.qml_module(\"library\")\n"
            "@pytest.mark.qml_dimension(\"read\")\n"
            "def test_read():\n"
            "    pass\n"
        )
        marked = find_marked_tests(tmp_path)
        assert len(marked) == 1
        mt = marked[0]
        mt_nodeid = mt["nodeid"]
        relpath = str(pyfile.relative_to(tmp_path))
        expected = f"{relpath}::test_read"
        assert mt_nodeid == expected


class TestDimensionStatus:
    def test_dimension_passed_all_green(self):
        testcases = [
            {"name": "test_read", "classname": "test_file", "nodeid": "test_file::test_read", "failure": None, "skipped": False, "time": 0.1, "suite": ""},
        ]
        marked = [{"nodeid": "test_file::test_read", "module": "library", "dimension": "read", "file": "test_file.py", "class": "", "function": "test_read"}]
        result = build_dimension_status("read", "library", testcases, marked, 8)
        assert result["status"] == "PASSED"

    def test_dimension_failed_when_test_fails(self):
        testcases = [
            {"name": "test_action", "classname": "test_file", "nodeid": "test_file::test_action", "failure": "assert 0", "skipped": False, "time": 0.1, "suite": ""},
        ]
        marked = [{"nodeid": "test_file::test_action", "module": "playback", "dimension": "primary_action", "file": "test_file.py", "class": "", "function": "test_action"}]
        result = build_dimension_status("primary_action", "playback", testcases, marked, 12)
        assert result["status"] == "FAILED"

    def test_dimension_missing_when_no_junit_evidence(self):
        testcases = []
        marked = [{"nodeid": "test_file::test_model", "module": "library", "dimension": "model_data", "file": "test_file.py", "class": "", "function": "test_model"}]
        result = build_dimension_status("model_data", "library", testcases, marked, 8)
        assert result["status"] == "MISSING"

    def test_dimension_not_applicable_when_no_markers(self):
        result = build_dimension_status("accessibility", "library", [], [], 5)
        assert result["status"] == "NOT_APPLICABLE"

    def test_skip_without_reason_is_missing(self, tmp_path):
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" skipped="1">
    <testcase classname="test_file" name="test_skip" time="0.0">
      <skipped message="" type="pytest.skip" />
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "skip_no_reason.xml"
        jfile.write_text(xml_content)
        testcases = parse_junit(jfile)
        marked = [{"nodeid": "test_file::test_skip", "module": "library", "dimension": "read", "file": "test_file.py", "class": "", "function": "test_skip"}]
        result = build_dimension_status("read", "library", testcases, marked, 8)
        assert result["status"] == "MISSING"


class TestScore:
    def test_score_all_passed(self):
        dims = {"m1": {"status": "PASSED", "weight": 10}}
        score = compute_module_score(dims)
        assert score == 100.0

    def test_score_all_failed(self):
        dims = {"m1": {"status": "FAILED", "weight": 10}}
        score = compute_module_score(dims)
        assert score == 0.0

    def test_score_weighted_mixed(self):
        dims = {
            "qml_module": {"status": "PASSED", "weight": 10},
            "qml_dimension": {"status": "FAILED", "weight": 10},
        }
        score = compute_module_score(dims)
        assert score == 50.0

    def test_score_empty_dimensions(self):
        score = compute_module_score({})
        assert score == 0.0

    def test_score_not_applicable_declared(self):
        dims = {"m1": {"status": "NOT_APPLICABLE_DECLARED", "weight": 10}}
        score = compute_module_score(dims)
        assert score == 100.0


class TestScoreMap:
    def test_failed_zero(self):
        assert SCORE_MAP["FAILED"] == 0.0

    def test_missing_zero(self):
        assert SCORE_MAP["MISSING"] == 0.0

    def test_passed_full(self):
        assert SCORE_MAP["PASSED"] == 1.0

    def test_not_applicable_declared_full(self):
        assert SCORE_MAP["NOT_APPLICABLE_DECLARED"] == 1.0

    def test_deferred_physical_full(self):
        assert SCORE_MAP["DEFERRED_PHYSICAL"] == 1.0


class TestModulesConfig:
    def test_config_has_modules(self, config):
        modules = config.get("modules", {})
        assert len(modules) > 0

    def test_has_library_module(self, config):
        assert "library" in config.get("modules", {})

    def test_module_has_weight(self, config):
        for _mod_name, mod_cfg in config.get("modules", {}).items():
            assert "weight" in mod_cfg
            assert isinstance(mod_cfg["weight"], int)
            assert mod_cfg["weight"] > 0

    def test_module_has_dimensions(self, config):
        for _mod_name, mod_cfg in config.get("modules", {}).items():
            assert "dimensions" in mod_cfg
            assert isinstance(mod_cfg["dimensions"], list)
