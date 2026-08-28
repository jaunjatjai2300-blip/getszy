"""Structural repository map: deterministic navigation without a model.

Most tests run against a tiny fixture tree so every answer is exact. One smoke
test builds the map over the real backend to prove it indexes the actual
repository, not just the fixture.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-repo-map-secret-32chars!!!!")

import repo_map  # noqa: E402
import agent_guard  # noqa: E402

APP = '''\
import helpers

@router.get("/widgets")
def list_widgets():
    return helpers.load_widgets()

@router.post("/widgets")
def create_widget():
    validate()
    return helpers.save_widget()

def validate():
    return True

class Store:
    def save(self):
        return helpers.persist()
'''

HELPERS = '''\
def load_widgets():
    return []

def save_widget():
    return persist()

def persist():
    return True
'''

TEST_FILE = '''\
from app import list_widgets, create_widget

def test_list():
    assert list_widgets is not None

def test_create():
    create_widget()
'''

BROKEN = "def oops(:\n    pass\n"   # deliberately invalid syntax


def _fixture(tmp_path) -> repo_map.RepoMap:
    (tmp_path / "app.py").write_text(APP, encoding="utf-8")
    (tmp_path / "helpers.py").write_text(HELPERS, encoding="utf-8")
    (tmp_path / "test_widgets.py").write_text(TEST_FILE, encoding="utf-8")
    (tmp_path / "broken.py").write_text(BROKEN, encoding="utf-8")
    return repo_map.build(tmp_path)


# ── build + where is X? ──────────────────────────────────────────────────────

def test_build_indexes_files_symbols_and_survives_a_broken_file(tmp_path):
    rm = _fixture(tmp_path)
    s = rm.summary()
    assert s["files"] == 3                 # broken.py is skipped, not fatal
    assert s["parse_errors"] == 1
    assert "broken.py" in rm.errors


def test_where_is_finds_functions_classes_and_methods(tmp_path):
    rm = _fixture(tmp_path)
    fn = rm.where_is("list_widgets")
    assert len(fn) == 1 and fn[0].kind == "function" and fn[0].file == "app.py"
    assert rm.where_is("Store")[0].kind == "class"
    save = rm.where_is("save")[0]
    assert save.kind == "method" and save.qualname == "Store.save"
    assert rm.where_is("nonexistent") == []


# ── who calls X? ─────────────────────────────────────────────────────────────

def test_who_calls_finds_callers_by_name_and_attribute(tmp_path):
    rm = _fixture(tmp_path)
    assert rm.who_calls("validate") == ["create_widget"]
    # persist() is called plainly in save_widget and as helpers.persist() in Store.save
    assert rm.who_calls("persist") == ["Store.save", "save_widget"]


# ── what routes reach X? ─────────────────────────────────────────────────────

def test_routes_are_detected_and_traced_to_callees(tmp_path):
    rm = _fixture(tmp_path)
    assert len(rm.routes) == 2
    get = rm.routes_using("list_widgets")            # handler IS the symbol
    assert len(get) == 1 and get[0].method == "GET" and get[0].path == "/widgets"
    # a route whose handler CALLS the symbol is included too
    assert any(r.method == "POST" for r in rm.routes_using("validate"))
    assert any(r.method == "GET" for r in rm.routes_using("load_widgets"))


# ── what tests cover X? ──────────────────────────────────────────────────────

def test_tests_covering_finds_referencing_test_files(tmp_path):
    rm = _fixture(tmp_path)
    assert rm.tests_covering("list_widgets") == ["test_widgets.py"]
    assert rm.tests_covering("create_widget") == ["test_widgets.py"]
    assert rm.tests_covering("persist") == []


# ── what is impacted by changing X? ──────────────────────────────────────────

def test_impact_of_unions_definition_callers_routes_and_tests(tmp_path):
    rm = _fixture(tmp_path)
    # load_widgets: defined in helpers.py, called from app.py (via a route)
    assert rm.impact_of("load_widgets") == ["app.py", "helpers.py"]
    # validate: defined + called + routed, all in app.py
    assert rm.impact_of("validate") == ["app.py"]


def test_build_is_rebuildable_idempotently(tmp_path):
    rm = _fixture(tmp_path)
    first = rm.summary()
    rm.build(tmp_path)                    # rebuild clears and re-indexes
    assert rm.summary() == first


# ── the map module is a protected control file ───────────────────────────────

def test_repo_map_is_self_protected():
    assert "backend/repo_map.py" in agent_guard.SELF_PROTECTED


# ── smoke: it indexes the REAL backend, not just the fixture ─────────────────

def test_smoke_over_the_real_backend():
    backend = Path(__file__).resolve().parent.parent
    rm = repo_map.build(backend)
    s = rm.summary()
    assert s["files"] > 50 and s["routes"] > 0
    # a known real symbol resolves to its real file
    defs = rm.where_is("build_config")
    assert any(d.file.endswith("agent_factory.py") for d in defs)
    # and a known real symbol has real callers
    assert rm.who_calls("build_config"), "build_config should have callers in the repo"
