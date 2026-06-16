# Changelog

All notable changes to reef-tools will be documented in this file.

## [0.2.0] — 2026-06-16

### Added
- `reef_tools.stats.stationarity` module with five non-parametric tests:
  - `pettitt_test` — rank-based CUSUM for step change detection
  - `mann_kendall` — monotonic trend with Theil-Sen slope
  - `rank_sum_test` — Mann-Whitney pre/post median comparison
  - `median_crossing_test` — Fisz median crossing test for serial independence
  - `rank_difference_test` — von Neumann ratio on ranks for serial dependence
- All functions exported at `reef_tools.stats` package level

## [0.1.0] — 2026-05-13

### Added
- Initial package scaffold with `src/` layout and 6 subpackages
- `reef_tools.utils.decorators` — `@timer` and `@cache_result` decorators
- `reef_tools.io.csv_helpers` — `read_csv_smart` with date parsing and filename metadata extraction
- `mkdocs` documentation with Material theme and `mkdocstrings` for auto-generated API docs
- CI/CD workflows: `ci.yml` (lint + test) and `docs.yml` (mkdocs deploy to GitHub Pages)
- pytest test suite with 16 tests
