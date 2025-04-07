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
- [ ] Commit changes following the agreed workflow (diff summary, plan update, commit, push).

## Phase 3: CI/CD and Finalization

- [ ] Set up `pytest` configuration.
- [x] Create GitHub Actions workflow (`.github/workflows/ci.yml`) for:
    - [x] Checking out code.
    - [x] Setting up Python and `uv`.
    - [x] Installing dependencies.
    - [x] Running tests (`pytest`).
    - [x] Building the package (`uv build`).
- [ ] Ensure CI passes.
- [x] Add basic usage documentation (README update or separate docs).
- [ ] Final commit and push.

## Future Considerations

- [ ] Publishing to PyPI.
- [ ] More advanced documentation (Sphinx/MkDocs).
- [ ] Additional features.