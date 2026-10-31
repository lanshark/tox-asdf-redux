from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from virtualenv import session_via_cli

from _tox_asdf_redux.discovery import spec_to_asdf_version


CURRENT = '{}.{}'.format(*sys.version_info[:2])
CURRENT_FULL = '{}.{}.{}'.format(*sys.version_info[:3])


@pytest.fixture
def asdf_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake asdf root whose only python install is the running one."""
    bin_dir = tmp_path / 'installs' / 'python' / CURRENT_FULL / 'bin'
    bin_dir.mkdir(parents=True)
    (bin_dir / 'python').symlink_to(sys.executable)
    monkeypatch.setenv('ASDF_ROOT', str(tmp_path))
    return tmp_path


def _discover(discovery: str, spec: str, tmp_path: Path):
    session = session_via_cli(
        ['--discovery', discovery, '-p', spec, str(tmp_path / 'venv')],
        env=dict(os.environ),
    )
    return session.interpreter


@pytest.mark.parametrize(('spec', 'expected'), [
    ('3.12', '3.12'),
    ('py312', '3.12'),
    ('python3.12', '3.12'),
    ('cpython3.12.1', '3.12.1'),
    ('py3', None),
    ('pypy3.10', None),
    ('/usr/bin/python3', None),
])
def test_spec_to_asdf_version(spec: str, expected: str | None) -> None:
    assert spec_to_asdf_version(spec) == expected


@pytest.mark.parametrize('discovery', ['asdf', 'asdf-strict'])
def test_finds_asdf_interpreter(
    asdf_root: Path, tmp_path: Path, discovery: str,
) -> None:
    interpreter = _discover(discovery, CURRENT, tmp_path)
    assert interpreter is not None
    assert Path(interpreter.system_executable).resolve() == (
        Path(sys.executable).resolve())


def test_strict_does_not_fall_back(asdf_root: Path, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match='failed to find interpreter'):
        _discover('asdf-strict', '2.7', tmp_path)


def test_default_falls_back_to_builtin(
    asdf_root: Path, tmp_path: Path,
) -> None:
    interpreter = _discover('asdf', sys.executable, tmp_path)
    assert interpreter is not None


def test_missing_asdf_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ASDF_ROOT', str(tmp_path / 'nope'))
    with pytest.raises(RuntimeError, match='failed to find interpreter'):
        _discover('asdf-strict', CURRENT, tmp_path)


@pytest.mark.parametrize(('mode', 'expected'), [
    (None, 'VIRTUALENV_DISCOVERY=asdf'),
    ('strict', 'VIRTUALENV_DISCOVERY=asdf-strict'),
])
def test_tox_plugin_sets_discovery(
    tmp_path: Path, mode: str | None, expected: str,
) -> None:
    ini = '[testenv]\nskip_install = true\n'
    if mode:
        ini += f'asdf_discovery = {mode}\n'
    (tmp_path / 'tox.ini').write_text(ini)
    result = subprocess.run(
        [sys.executable, '-m', 'tox', 'config', '-e', 'py', '-k', 'set_env'],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert expected in result.stdout


def test_tox_plugin_off(tmp_path: Path) -> None:
    (tmp_path / 'tox.ini').write_text(
        '[testenv]\nskip_install = true\nasdf_discovery = off\n')
    result = subprocess.run(
        [sys.executable, '-m', 'tox', 'config', '-e', 'py', '-k', 'set_env'],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert 'VIRTUALENV_DISCOVERY' not in result.stdout
