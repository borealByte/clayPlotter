# Project Plan: Modernizing clayPlotter

This plan outlines the steps to transform the `clayPlotter` project into a modern, installable Python package with testing, CI/CD, and best practices.

## Phase 1: Setup and Restructuring

- [x] Choose and configure packaging tool (`uv` with `pyproject.toml`).
- [x] Choose and configure versioning tool (`Commitizen`).
- [x] Create initial `project-plan.md` (this file).
- [x] Create directory structure (`src/clayPlotter`, `notebooks`, `tests`).
- [x] Move `choropleth_plotter.py` to `src/clayPlotter/plotter.py`.
- [x] Move `test.ipynb` to `notebooks/`.
- [x] Create `src/clayPlotter/__init__.py`.
- [x] Configure `pyproject.toml` for basic project metadata and `uv`.
- [x] Configure `Commitizen` (`.cz.toml` or in `pyproject.toml`).
- [ ] Commit initial structure and configuration.

## Phase 2: Refactoring and TDD

*(Repeat for each logical piece of functionality)*
- [x] Analyze functionality in `src/clayPlotter/plotter.py`.
- [x] Define Object-Oriented structure.
- [ ] Identify first function/method to refactor/implement.
- [ ] TDD: Implement shapefile downloading/caching/reading in GeoDataManager.
- [x] Write tests for the function/method (`tests/test_...`).
- [x] Implement/Refactor the function/method in `src/clayPlotter/`.
- [x] Ensure tests pass.
- [x] TDD: Implement user data loading and validation (from YAML/CSV).
- [ ] TDD: Implement core ChoroplethPlotter class and plot generation.
  - [x] Write tests for ChoroplethPlotter (`tests/test_plotter.py`).
  - [x] Implement minimal ChoroplethPlotter class structure (`src/clayPlotter/plotter.py`).
  - [x] Ensure tests pass against minimal structure.
  - [x] Implement core logic (`_prepare_data`, `plot`) in `ChoroplethPlotter`.
  - [x] Ensure tests pass for core logic implementation.
- [ ] Keep files under ~350 lines (break down if needed).
- [x] Commit changes following the agreed workflow (diff summary, plan update, commit, push).
- [x] **Map Styling & Refinement (Iteration 1 - `restor_map_beauty` branch):**
  - [x] Create feature branch (`restor_map_beauty`).
  - [x] Implement basic CI via GitHub Actions (`python-package.yml`).
  - [x] Add CI badge to README.
  - [x] Update test notebook (`test.ipynb`) to use `ChoroplethPlotter` class.
  - [x] Refine `plotter.py` and YAML configs (`usa_states.yaml`, `canada_provinces.yaml`) to:
    - [x] Implement lake plotting based on config.
    - [x] Implement label placement (direct, offset annotations, clipping) based on config.
    - [x] Correct legend/colorbar handling (single, vertical).
    - [x] Make map projection configurable (`target_crs` in YAML).
    - [x] Apply appropriate projections (Albers for USA, Lambert for Canada).
    - [x] Set map extent dynamically for projected maps.
    - [x] Add 10m admin layer for neighbor plotting.
    - [x] Plot neighboring countries (Admin 0).
    - [x] Clip neighbors to map viewport.
    - [x] Add semi-transparent label backgrounds.
    - [x] Simplify label offset config (removed `small_regions`).
    - [x] Adjust offset values for projected coordinates.
  - [x] Commit and push styling/refinement changes.

## Phase 3: CI/CD and Finalization

- [ ] Set up `pytest` configuration.
- [x] Create GitHub Actions workflow (`.github/workflows/python-package.yml`) for:
    - [x] Checking out code (`actions/checkout@v4`).
    - [x] Setting up Python (`actions/setup-python@v4`).
    - [x] Installing dependencies (`pip install build pytest .`).
    - [x] Running tests (`pytest`).
    - [x] Building the package (`python -m build`).
- [ ] Ensure CI passes (requires push to GitHub).
- [x] Add CI status badge placeholder to `README.md`.
- [x] Add basic usage documentation (README update or separate docs).
- [ ] Final commit and push.

## Future Considerations

- [ ] Publishing to PyPI.
- [ ] More advanced documentation (Sphinx/MkDocs).
- [ ] Additional features.