from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest
from virtualenv import session_via_cli

from _tox_asdf_redux.discovery import Asdf, AsdfStrict, spec_to_asdf_version


CURRENT = '{}.{}'.format(*sys.version_info[:2])
CURRENT_FULL = '{}.{}.{}'.format(*sys.version_info[:3])
# a version that is never installed in the fake asdf root
MISSING = '2.7'

ASDF_ENV_VARS = ('ASDF_DATA_DIR', 'ASDF_ROOT')
NOT_FOUND = 'failed to find interpreter'


def _make_asdf_root(root: Path, *versions: str) -> Path:
    """Create a fake asdf data dir; every install links to this python."""
    installs = root / 'installs' / 'python'
    installs.mkdir(parents=True)
    for version in versions:
        bin_dir = installs / version / 'bin'
        bin_dir.mkdir(parents=True)
        (bin_dir / 'python').symlink_to(sys.executable)
    return root


@pytest.fixture(autouse=True)
def _isolate_asdf_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's real asdf settings out of the tests."""
    for env_var in ASDF_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


@pytest.fixture(params=ASDF_ENV_VARS)
def asdf_root(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """A fake asdf root whose only python install is the running one."""
    root = _make_asdf_root(tmp_path / 'asdf', CURRENT_FULL)
    monkeypatch.setenv(request.param, str(root))
    return root


@pytest.fixture
def unmatched_asdf_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """A fake asdf root with an install that never matches CURRENT."""
    root = _make_asdf_root(tmp_path / 'asdf', '2.7.18')
    monkeypatch.setenv('ASDF_DATA_DIR', str(root))
    return root


def _discover(discovery: str, specs: str | list[str], tmp_path: Path):
    if isinstance(specs, str):
        specs = [specs]
    args = ['--discovery', discovery]
    for spec in specs:
        args += ['-p', spec]
    session = session_via_cli(
        [*args, str(tmp_path / 'venv')], env=dict(os.environ))
    return session.interpreter


def _assert_is_current(interpreter) -> None:
    assert interpreter is not None
    assert Path(interpreter.system_executable).resolve() == (
        Path(sys.executable).resolve())


# -- spec parsing ------------------------------------------------------------

@pytest.mark.parametrize(('spec', 'expected'), [
    ('3.12', '3.12'),
    ('py312', '3.12'),
    ('python3.12', '3.12'),
    ('cpython3.12.1', '3.12.1'),
    ('py3', None),
    ('pypy3.10', None),
    ('/usr/bin/python3', None),
    ('3.13t', None),
])
def test_spec_to_asdf_version(spec: str, expected: str | None) -> None:
    assert spec_to_asdf_version(spec) == expected


# -- virtualenv discovery ----------------------------------------------------

@pytest.mark.parametrize('discovery', ['asdf', 'asdf-strict'])
def test_finds_asdf_interpreter(
    asdf_root: Path, tmp_path: Path, discovery: str,
) -> None:
    _assert_is_current(_discover(discovery, CURRENT, tmp_path))


def test_strict_does_not_fall_back(asdf_root: Path, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=NOT_FOUND):
        _discover('asdf-strict', MISSING, tmp_path)


def test_default_falls_back_for_path(asdf_root: Path, tmp_path: Path) -> None:
    _assert_is_current(_discover('asdf', sys.executable, tmp_path))


def test_strict_rejects_path(asdf_root: Path, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=NOT_FOUND):
        _discover('asdf-strict', sys.executable, tmp_path)


def test_default_falls_back_when_version_not_in_asdf(
    unmatched_asdf_root: Path, tmp_path: Path,
) -> None:
    _assert_is_current(_discover('asdf', CURRENT, tmp_path))


def test_strict_fails_when_version_not_in_asdf(
    unmatched_asdf_root: Path, tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match=NOT_FOUND):
        _discover('asdf-strict', CURRENT, tmp_path)


def test_default_falls_back_when_asdf_root_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ASDF_DATA_DIR', str(tmp_path / 'nope'))
    _assert_is_current(_discover('asdf', CURRENT, tmp_path))


def test_strict_fails_when_asdf_root_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ASDF_DATA_DIR', str(tmp_path / 'nope'))
    with pytest.raises(RuntimeError, match=NOT_FOUND):
        _discover('asdf-strict', CURRENT, tmp_path)


def test_multiple_specs_uses_first_asdf_match(
    asdf_root: Path, tmp_path: Path,
) -> None:
    _assert_is_current(_discover('asdf-strict', [MISSING, CURRENT], tmp_path))


# -- packaging ---------------------------------------------------------------

def test_virtualenv_discovery_entry_points() -> None:
    eps = {
        ep.name: ep.load()
        for ep in entry_points(group='virtualenv.discovery')
        if ep.name.startswith('asdf')
    }
    assert eps == {'asdf': Asdf, 'asdf-strict': AsdfStrict}


def test_tox_entry_point() -> None:
    (ep,) = [
        ep for ep in entry_points(group='tox') if ep.name == 'asdf-redux'
    ]
    assert ep.value == '_tox_asdf_redux.plugin'
    ep.load()


# -- tox plugin --------------------------------------------------------------

def _tox(cwd: Path, *args: str, check: bool = True):
    return subprocess.run(
        [sys.executable, '-m', 'tox', *args],
        cwd=cwd, capture_output=True, text=True, check=check,
    )


def _write_tox_ini(path: Path, *lines: str) -> None:
    (path / 'tox.ini').write_text(
        '\n'.join(['[testenv]', 'skip_install = true', *lines, '']))


@pytest.mark.parametrize(('mode', 'expected'), [
    (None, 'VIRTUALENV_DISCOVERY=asdf'),
    ('strict', 'VIRTUALENV_DISCOVERY=asdf-strict'),
])
def test_tox_plugin_sets_discovery(
    tmp_path: Path, mode: str | None, expected: str,
) -> None:
    _write_tox_ini(tmp_path, *([f'asdf_discovery = {mode}'] if mode else []))
    result = _tox(tmp_path, 'config', '-e', 'py', '-k', 'set_env')
    assert expected in result.stdout


def test_tox_plugin_off(tmp_path: Path) -> None:
    _write_tox_ini(tmp_path, 'asdf_discovery = off')
    result = _tox(tmp_path, 'config', '-e', 'py', '-k', 'set_env')
    assert 'VIRTUALENV_DISCOVERY' not in result.stdout


def test_tox_plugin_rejects_invalid_mode(tmp_path: Path) -> None:
    _write_tox_ini(tmp_path, 'asdf_discovery = bogus')
    result = _tox(tmp_path, 'run', '-e', 'py', check=False)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "asdf_discovery: unexpected value 'bogus'" in output
    assert 'default, strict, off' in output


# -- end to end: tox builds an environment through the plugin ---------------

@pytest.fixture
def strict_umask():
    """tox refuses to use a group/world-writable .tox directory."""
    old = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(old)


@pytest.fixture
def tox_project(tmp_path: Path, strict_umask: None) -> Path:
    project = tmp_path / 'project'
    project.mkdir()
    _write_tox_ini(
        project,
        f'base_python = {CURRENT}',
        'asdf_discovery = strict',
        'commands = python -c "import sys; print(sys.version_info[:2])"',
    )
    return project


def test_tox_run_uses_asdf_interpreter(
    asdf_root: Path, tox_project: Path,
) -> None:
    result = _tox(tox_project, 'run', '-e', 'py', check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(sys.version_info[:2]) in result.stdout


def test_tox_run_strict_fails_without_asdf_match(
    unmatched_asdf_root: Path, tox_project: Path,
) -> None:
    result = _tox(tox_project, 'run', '-e', 'py', check=False)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert 'could not find python interpreter' in output, output
