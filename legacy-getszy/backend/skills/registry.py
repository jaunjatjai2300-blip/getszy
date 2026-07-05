"""Getszy Skills registry.

A Skill is a single reusable admin action with:
  - name      : unique slug (e.g. 'scan_trending')
  - title     : human label
  - icon      : lucide-react icon name (frontend hint)
  - category  : grouping ('commerce', 'media', 'marketing', 'devops', 'analytics')
  - badge     : 'free' or 'pro'
  - params    : JSON-schema-ish description of accepted params
  - run(p, ctx): async callable returning a dict result

Skills are imported and registered at startup. The Copilot uses the registry
to turn natural language into skill invocations.
"""
from __future__ import annotations
from typing import Callable, Awaitable, Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Skill:
    name: str
    title: str
    description: str
    category: str
    icon: str = 'Sparkles'
    badge: str = 'free'  # free | pro | elite
    params: Dict[str, Any] = field(default_factory=dict)
    run: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop('run', None)
        return d


class _Registry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def all(self) -> List[Skill]:
        return list(self._skills.values())

    def by_category(self) -> Dict[str, List[Skill]]:
        out: Dict[str, List[Skill]] = {}
        for s in self._skills.values():
            out.setdefault(s.category, []).append(s)
        return out


registry = _Registry()


def register(**kwargs):
    """Decorator: @register(name='...', title='...', ...)"""
    def deco(fn):
        skill = Skill(run=fn, **kwargs)
        registry.register(skill)
        return fn
    return deco
