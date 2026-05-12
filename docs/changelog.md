# Changelog

All notable changes to reef-tools will be documented in this file.

## [0.1.0] — 2026-05-13

### Added
- Initial package scaffold with `src/` layout and 6 subpackages
- `reef_tools.utils.decorators` — `@timer` and `@cache_result` decorators
- `reef_tools.io.csv_helpers` — `read_csv_smart` with date parsing and filename metadata extraction
- `mkdocs` documentation with Material theme and `mkdocstrings` for auto-generated API docs
- CI/CD workflows: `ci.yml` (lint + test) and `docs.yml` (mkdocs deploy to GitHub Pages)
- pytest test suite with 16 tests
