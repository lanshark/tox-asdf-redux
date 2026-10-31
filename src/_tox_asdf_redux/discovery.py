"""virtualenv discovery plugins that look up interpreters installed by asdf."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from asdf_inspect import find_asdf_python_executable
from asdf_inspect.exceptions import ASDFInspectError
from virtualenv.discovery.builtin import Builtin


try:  # virtualenv >= 21 moved interpreter introspection to python-discovery
    from python_discovery import PythonInfo, PythonSpec
except ImportError:  # pragma: no cover
    from virtualenv.discovery.py_info import PythonInfo
    from virtualenv.discovery.py_spec import PythonSpec


if TYPE_CHECKING:
    from pathlib import Path


log = logging.getLogger(__name__)


def spec_to_asdf_version(string_spec: str) -> str | None:
    """Convert a virtualenv/tox python spec to an asdf-style version.

    Returns ``None`` when the spec is not something asdf can satisfy
    (a path, a non-CPython implementation, or a bare major version).
    """
    spec = PythonSpec.from_string_spec(string_spec)
    if spec.path is not None:
        return None
    if spec.implementation not in (None, 'cpython', 'python', 'py'):
        return None
    if spec.major is None or spec.minor is None:
        return None
    if getattr(spec, 'free_threaded', False):
        return None
    parts = [spec.major, spec.minor]
    if spec.micro is not None:
        parts.append(spec.micro)
    return '.'.join(map(str, parts))


class Asdf(Builtin):
    """Prefer asdf-installed interpreters, fall back to builtin discovery."""

    fall_back_to_builtin = True

    def run(self) -> PythonInfo | None:
        for string_spec in self.python_spec:
            python_info = self._find_asdf_interpreter(string_spec)
            if python_info is not None:
                return python_info
        if self.fall_back_to_builtin:
            log.debug('asdf: falling back to builtin discovery')
            return super().run()
        return None

    def _find_asdf_interpreter(self, string_spec: str) -> PythonInfo | None:
        version = spec_to_asdf_version(string_spec)
        if version is None:
            log.debug('asdf: spec %r is not an asdf version', string_spec)
            return None
        try:
            exe = find_asdf_python_executable(version)
        except ASDFInspectError as exc:
            log.debug('asdf: lookup of %s failed: %s', version, exc)
            return None
        if exe is None:
            log.debug('asdf: no installed version matches %s', version)
            return None
        log.debug('asdf: %s -> %s', string_spec, exe)
        return self._python_info(exe)

    def _python_info(self, exe: Path) -> PythonInfo | None:
        return PythonInfo.from_exe(str(exe), self.app_data, env=self._env)

    def __repr__(self) -> str:
        spec = (
            self.python_spec[0] if len(self.python_spec) == 1
            else self.python_spec
        )
        return f'{type(self).__name__} discover of python_spec={spec!r}'


class AsdfStrict(Asdf):
    """Only use asdf-installed interpreters; never fall back."""

    fall_back_to_builtin = False
