# 2026-08 Home Assistant Compatibility Upgrade

Upgraded the integration to the newest Home Assistant release (2026.8.0) and its
matching dependency pins.

## Dependency bumps

`requirements.txt`:

| Package      | Before  | After   |
| ------------ | ------- | ------- |
| homeassistant| 2025.11 | 2026.8.0|
| aiohttp      | unpinned| 3.14.3  |
| yarl         | unpinned| 1.24.5  |
| requests     | (missing, but imported)| 2.34.2 |
| aiohttp_cors | 0.7.0   | removed (unused) |
| attr         | unpinned| removed (unused) |
| atomicwrites | 1.4.0   | removed (unused) |

`requirements_dev.txt`:

| Package                                 | Before  | After    |
| ---------------------------------------- | ------- | -------- |
| mypy                                     | 0.910   | 2.3.0    |
| pytest-homeassistant-custom-component    | 0.13.36 | 0.13.354 |
| pytest-aiohttp                           | 0.3.0   | 1.1.1    |
| pytest                                   | pinned 6.2.5 | unpinned (resolved transitively — `pytest-homeassistant-custom-component` now hard-pins `pytest==9.0.3` itself) |
| pylint                                   | 2.8.3   | unpinned (latest) |

`aiohttp_cors`, `attr`, and `atomicwrites` were never actually imported anywhere in
`custom_components/swatch` — dropped as dead weight rather than upgraded.

## Code changes required by the bump

- **`config_flow.py`** — `homeassistant.data_entry_flow.FlowResult` →
  `homeassistant.config_entries.ConfigFlowResult`, the current recommended return type
  for config flow steps.
- **`api.py`** — dropped the `async_timeout` dependency in favor of the stdlib
  `asyncio.timeout()` (HA itself no longer depends on the `async_timeout` backport now
  that the minimum supported Python has `asyncio.timeout` built in).
- **`hacs.json`** — minimum Home Assistant version bumped to `2026.8.0`.
- Removed stale `__pycache__/*.cpython-39.pyc` files that were accidentally committed,
  and added `__pycache__/`/`*.pyc` to `.gitignore` so it doesn't happen again.
- `.pre-commit-config.yaml` — bumped pyupgrade (`--py313-plus`), black, codespell,
  pre-commit-hooks and mirrors-prettier to current releases.

## Validated

- `pip install -r requirements_dev.txt` resolves and installs cleanly (this exercises the
  real dependency graph, including confirming `pytest-homeassistant-custom-component`
  0.13.354's hard pins on `pytest==9.0.3` / `homeassistant==2026.8.0` don't conflict with
  anything else in the file).
- Every module in `custom_components/swatch` imports cleanly against the real installed
  `homeassistant` 2026.8.0 package.
- `pre-commit run --all-files` clean; `flake8` clean other than one pre-existing,
  unrelated nit in `binary_sensor.py` (an f-string with no placeholders).
