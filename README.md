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
`$ASDF_DATA_DIR/installs/python` is used (default `~/.asdf`; `ASDF_ROOT`
is also honoured for backward compatibility).

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

Coverage (includes the tox subprocesses started by the tests):

```bash
uv run coverage run -m pytest
uv run coverage combine
uv run coverage report
```

CI combines coverage from every Python version and shows it on the workflow
run's summary page; an HTML report is attached as the `coverage-html`
artifact.
CI fails if total coverage drops below 90% (`fail_under` in `pyproject.toml`).

## Releasing

`main` only accepts changes through pull requests, so the version bump goes
through a PR before tagging:

1. Bump the version on a branch and open a PR:

   ```bash
   git checkout -b release-X.Y.Z
   uv version --bump patch   # or minor / major
   git commit -am "Release X.Y.Z"
   git push -u origin release-X.Y.Z
   ```

2. Merge the PR once CI passes.
3. Tag the merged `main` and push the tag:

   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z -m "tox-asdf-redux X.Y.Z"
   git push origin vX.Y.Z
   ```

4. Create a GitHub release for the tag with the release notes.

Pushing the tag starts the `Publish to PyPI` workflow. It runs CI, checks that
the tag matches the version in `pyproject.toml`, builds with `uv build` and
publishes using PyPI trusted publishing. Always tag after the merge, so the
tagged commit is on `main`.

NOTE: Adapted from [tox-pyenv-redux][tox-pyenv-redux].

[tox]: https://tox.wiki/
[asdf]: https://github.com/asdf-vm/asdf
[discovery]: https://virtualenv.pypa.io/en/latest/extend.html
[tox-uv]: https://github.com/tox-dev/tox-uv
[tox-pyenv-redux]: https://github.com/un-def/tox-pyenv-redux
