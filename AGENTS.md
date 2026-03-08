# Repository Guidelines

## Project Structure & Module Organization
`burst.py` is the Kodi entrypoint and forwards work into `burst/`, which contains the core search pipeline (`burst.py`, `provider.py`, `client.py`, `filtering.py`, `normalize.py`, `utils.py`).
`burst/providers/` contains provider metadata (`providers.json`), provider overrides/defaults (`definitions.py`), and tracker icons (`icons/`).
`resources/settings.xml` holds addon settings (provider sections are generated), `resources/language/*/strings.po` holds translations, and `resources/site-packages/` contains vendored third-party libraries.
Use `scripts/` for maintenance tasks such as settings generation, localization checks/merges, and changelog generation.

## Build, Test, and Development Commands
- `pip3 install -r requirements.txt`: install developer dependencies.
- `make check`: run `flake8` using `setup.cfg`.
- `./scripts/xgettext.sh`: validate translation `.po` files.
- `make`: build `script.elementum.burst-<version>.zip` from current `HEAD`.
- `make settings`: regenerate provider blocks in `resources/settings.xml` after editing `burst/providers/providers.json`.
- `make locales`: merge `resources/language/messages.pot` into each locale file.

## Coding Style & Naming Conventions
Use Python with 4-space indentation and keep existing UTF-8 module headers where present.
Follow `flake8` rules from `setup.cfg` (`max-line-length = 370`, several ignored legacy rules, and `resources/site-packages/` excluded).
Use `snake_case` for functions, variables, and modules; use `UPPER_CASE` for constants.
Provider IDs should remain lowercase and stable because they map directly to settings keys (for example `use_<provider_id>`).

## Testing Guidelines
CI currently enforces linting and translation validation, not a full unit-test suite.
Before opening a PR, run `make check` and `./scripts/xgettext.sh`.
For provider/network changes, run focused scripts when relevant (for example `python3 scripts/antizapret_test.py`) and include key results in the PR description.

## Commit & Pull Request Guidelines
Use concise, imperative commit subjects, optionally with issue/PR refs (examples from history: `Fix multiline torrent name (#489)`, `Add Knaben (#485)`).
Keep version bumps in dedicated commits (for example `Version 0.0.97`).
PRs should include: purpose, impacted providers/modules, verification commands run, and related issue links.
If you update `addon.xml` version, keep release tags and packaged artifact versions aligned.
