# tox-asdf-redux

A [tox][tox] plugin using [asdf][asdf] to find Python executables.

Requires tox 4 and Python 3.11+.

## Installation

Install the plugin into the same environment as tox:

```bash
uv tool install tox --with tox-asdf-redux
# or
pip install tox-asdf-redux
```

## How it works

The plugin registers two [virtualenv discovery][discovery] plugins and tells
tox to use one of them via `VIRTUALENV_DISCOVERY`. When a tox environment asks
for e.g. `py312`, `python3.12` or `3.12`, the newest matching interpreter under
`$ASDF_ROOT/installs/python` (default `~/.asdf`) is used.

## Configuration

Set `asdf_discovery` per environment (or in `env_run_base` / `[testenv]`):

| value     | behaviour                                                        |
|-----------|------------------------------------------------------------------|
| `default` | use asdf interpreters, fall back to virtualenv builtin discovery |
| `strict`  | only use asdf interpreters; fail if none matches                 |
| `off`     | do not touch interpreter discovery                               |

```toml
[tool.tox.env_run_base]
asdf_discovery = "strict"
```

Note: [tox-uv][tox-uv] replaces virtualenv with `uv venv`, so this plugin has
no effect when tox-uv is installed.

## Development

```bash
uv sync
uv run pytest
uv run tox
```

## Releasing

1. Bump `version` in `pyproject.toml` (`uv version --bump minor`), commit.
2. Tag and push: `git tag v0.2.0 && git push origin v0.2.0`.

The `Publish to PyPI` workflow runs CI, checks that the tag matches the project
version, builds with `uv build` and publishes using PyPI trusted publishing.

NOTE: Adapted from [tox-pyenv-redux][tox-pyenv-redux].

[tox]: https://tox.wiki/
[asdf]: https://github.com/asdf-vm/asdf
[discovery]: https://virtualenv.pypa.io/en/latest/extend.html
[tox-uv]: https://github.com/tox-dev/tox-uv
[tox-pyenv-redux]: https://github.com/un-def/tox-pyenv-redux
