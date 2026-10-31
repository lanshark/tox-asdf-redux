from __future__ import annotations

from typing import TYPE_CHECKING

from tox.plugin import impl


if TYPE_CHECKING:
    from tox.config.sets import EnvConfigSet


_DISCOVERY_ENV_VAR = 'VIRTUALENV_DISCOVERY'

ASDF_DISCOVERY_SETTING = 'asdf_discovery'

# setting value -> virtualenv discovery entry point name (None = disabled)
_DISCOVERY_MODES: dict[str, str | None] = {
    'default': 'asdf',
    'strict': 'asdf-strict',
    'off': None,
}


@impl
def tox_add_env_config(env_conf: EnvConfigSet) -> None:
    env_conf.add_config(
        ASDF_DISCOVERY_SETTING,
        of_type=str,
        default='default',
        desc=(
            'asdf interpreter discovery mode: '
            + ', '.join(_DISCOVERY_MODES)
        ),
    )
    value = env_conf[ASDF_DISCOVERY_SETTING]
    try:
        discovery = _DISCOVERY_MODES[value]
    except KeyError:
        raise ValueError(
            f'{ASDF_DISCOVERY_SETTING}: unexpected value {value!r}, '
            f'expected one of: {", ".join(_DISCOVERY_MODES)}'
        ) from None
    if discovery is not None:
        env_conf['set_env'].update({_DISCOVERY_ENV_VAR: discovery})
