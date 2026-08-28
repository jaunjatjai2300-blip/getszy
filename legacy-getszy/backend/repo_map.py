"""Agent Factory — native structural repository map.

Deterministic repository intelligence built from the Python AST alone. It does
NOT replace `codebase_rag` (semantic search) and adds no second RAG or LLM: this
is a *structural* index — symbols, imports, calls, routes, tests — that answers
navigation questions exactly and cheaply, so a coding agent stops rediscovering
the same facts.

What it represents, where the source makes it available:
  files/modules · classes · functions/methods · imports · calls · FastAPI routes
  · test references · per-file symbol definitions.

Questions it answers, all without a model:
  where is X?  ·  who calls X?  ·  what routes reach X?  ·  what tests cover X?
  ·  what files are likely impacted by changing X?

The map is rebuildable (`build()` again) and fully testable against a fixture
tree — nothing here depends on a running service.
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("getszy.agent.repomap")

_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head",
                 "api_route", "websocket"}
_SKIP_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}


@dataclass
class Symbol:
    name: str
    kind: str            # class | function | method
    module: str
    file: str
    lineno: int
    qualname: str


@dataclass
class Route:
    method: str
    path: str
    handler: str         # qualname of the handler function
    module: str
    file: str
    lineno: int


def _callee_name(call: ast.Call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _route_from_decorator(dec):
    """(@router.get("/x")) -> ("GET", "/x"); returns None if not a route decorator."""
    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
        method = dec.func.attr.lower()
        if method in _HTTP_METHODS:
            path = None
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                path = dec.args[0].value
            return method.upper(), (path or "")
    return None


def _calls_in(node) -> set:
    """Every callee name reachable inside a function body."""
    callees = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = _callee_name(sub)
            if name:
                callees.add(name)
    return callees


class RepoMap:
    """A structural index of a Python source tree. Deterministic and rebuildable."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}                 # rel_file -> module
        self.symbols: dict[str, list] = {}              # name -> [Symbol]
        self.qual_file: dict[str, str] = {}             # qualname -> rel_file
        self.imports: dict[str, set] = {}               # module -> {imported names}
        self.calls: dict[str, set] = {}                 # caller qualname -> {callee names}
        self.routes: list = []                          # [Route]
        self.tests: dict[str, set] = {}                 # test file -> {referenced names}
        self.defs_by_file: dict[str, set] = {}          # rel_file -> {defined names}
        self.errors: dict[str, str] = {}                # rel_file -> parse error
        self.root: Path | None = None

    # ── build ────────────────────────────────────────────────────────────────

    def build(self, root, *, recursive: bool = True) -> "RepoMap":
        """Index every .py file under `root`. Idempotent: clears prior state."""
        self.__init__()
        self.root = Path(root).resolve()
        paths = self.root.rglob("*.py") if recursive else self.root.glob("*.py")
        for path in sorted(paths):
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            rel = path.relative_to(self.root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
            except SyntaxError as e:                     # a broken file must not sink the map
                self.errors[rel] = f"SyntaxError: {e}"
                continue
            self._index_module(rel, path.stem, tree)
        return self

    def _index_module(self, rel: str, module: str, tree: ast.Module) -> None:
        self.files[rel] = module
        self.imports.setdefault(module, set())
        self.defs_by_file.setdefault(rel, set())
        is_test = Path(rel).name.startswith("test_")

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._index_import(module, node)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_symbol(rel, module, node.name, "function", node.name, node.lineno)
                self.calls[node.name] = _calls_in(node)
                self._index_routes(rel, module, node, handler=node.name)
            elif isinstance(node, ast.ClassDef):
                self._add_symbol(rel, module, node.name, "class", node.name, node.lineno)
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qual = f"{node.name}.{sub.name}"
                        self._add_symbol(rel, module, sub.name, "method", qual, sub.lineno)
                        self.calls[qual] = _calls_in(sub)
                        self._index_routes(rel, module, sub, handler=qual)

        if is_test:
            self.tests[rel] = {
                n.id for n in ast.walk(tree) if isinstance(n, ast.Name)
            } | {
                a.attr for a in ast.walk(tree) if isinstance(a, ast.Attribute)
            }

    def _index_import(self, module: str, node) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports[module].add(alias.name.split(".")[0])
        else:  # ImportFrom
            if node.module:
                self.imports[module].add(node.module.split(".")[0])
            for alias in node.names:
                self.imports[module].add(alias.name)

    def _index_routes(self, rel: str, module: str, fn, *, handler: str) -> None:
        for dec in getattr(fn, "decorator_list", []):
            parsed = _route_from_decorator(dec)
            if parsed:
                method, path = parsed
                self.routes.append(Route(method=method, path=path, handler=handler,
                                         module=module, file=rel, lineno=fn.lineno))

    def _add_symbol(self, rel, module, name, kind, qualname, lineno) -> None:
        self.symbols.setdefault(name, []).append(
            Symbol(name=name, kind=kind, module=module, file=rel, lineno=lineno, qualname=qualname))
        self.qual_file[qualname] = rel
        self.defs_by_file[rel].add(name)

    # ── queries (all deterministic, no model) ─────────────────────────────────

    def where_is(self, symbol: str) -> list:
        """Every definition of a symbol."""
        return list(self.symbols.get(symbol, []))

    def who_calls(self, symbol: str) -> list:
        """Qualnames of functions/methods whose body calls the symbol."""
        return sorted(q for q, callees in self.calls.items() if symbol in callees)

    def routes_using(self, symbol: str) -> list:
        """Routes whose handler IS the symbol or calls it."""
        callers = set(self.who_calls(symbol))
        out = []
        for r in self.routes:
            if r.handler == symbol or r.handler.split(".")[-1] == symbol or r.handler in callers:
                out.append(r)
        return out

    def tests_covering(self, symbol: str) -> list:
        """Test files that reference the symbol by name."""
        return sorted(f for f, names in self.tests.items() if symbol in names)

    def impact_of(self, symbol: str) -> list:
        """Files likely affected by changing the symbol: where it is defined, who
        calls it, which routes reach it, and which tests cover it."""
        files = set()
        for s in self.where_is(symbol):
            files.add(s.file)
        for q in self.who_calls(symbol):
            if q in self.qual_file:
                files.add(self.qual_file[q])
        for r in self.routes_using(symbol):
            files.add(r.file)
        files.update(self.tests_covering(symbol))
        return sorted(files)

    def summary(self) -> dict:
        return {
            "files": len(self.files),
            "symbols": sum(len(v) for v in self.symbols.values()),
            "routes": len(self.routes),
            "tests": len(self.tests),
            "parse_errors": len(self.errors),
        }


def build(root, *, recursive: bool = True) -> RepoMap:
    """Build and return a fresh RepoMap for a source tree."""
    return RepoMap().build(root, recursive=recursive)


__all__ = ["RepoMap", "Route", "Symbol", "build"]
