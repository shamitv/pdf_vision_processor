# PyPI Distribution Plan

## Goals
- Ship the existing FastAPI PDF Vision Processor as an installable package named `pdf-vision-processor`.
- Provide a zero-code startup path: `pip install pdf-vision-processor` followed by a single CLI command that serves the API using the packaged assets.
- Preserve backwards compatibility with the current repo structure so local developers can continue to run `run.py` without behavioral changes.
- Establish a repeatable release workflow (build, test, publish) that can be triggered manually or from CI.

## Deliverables
1. `setup.py`-driven packaging (mirroring the `shamitv/llama_cpp` approach) with metadata, dependencies, versioning, and a `console_scripts` entry point managed via setuptools plus a helper build script.
2. Source package layout under `pdf_vision_processor/` (match current `app` package) plus inclusion of templates, static assets, and default config files in wheels.
3. CLI shim `pdf-vision-processor` that loads environment variables, applies runtime options, and boots Uvicorn with `app.main:app`.
4. Documentation update covering installation, configuration, and server invocation for consumers.
5. Release checklist + automation scripts for building and uploading to TestPyPI/PyPI.

## Status Snapshot (2025-11-21)
| Workstream | Status | Notes | Next Steps |
| --- | --- | --- | --- |
| A – Packaging/Layout | ✅ Completed | Code now ships from `pdf_vision_processor/`, legacy `app/` is a shim, `setup.py`/`pyproject.toml`/`MANIFEST.in` land, version lives in `_version.py`. | Audit sample fixtures to ensure wheel stays small; decide whether `_version.py` should export richer metadata. |
| B – CLI/Server | ✅ Completed | `pdf-vision-processor` CLI with layered settings, `.env` loading, docs refreshed, `run.py` delegates to CLI. | Consider future subcommands (e.g., `serve`, `process-once`) after feedback. |
| C – Testing/Validation | ⚠️ Partially done | Added unit coverage for settings + CLI; pytest workflow documented. | Add end-to-end smoke test that installs wheel in temp venv, runs CLI, and verifies `/health`; document/automate Windows coverage decision. |
| D – Release Workflow | ⚠️ Partially done | `scripts/build_dist.py` handles bump/build/twine check; publishing checklist added. | Wire GitHub Actions for tagged builds, run TestPyPI dry run, store PyPI/TestPyPI tokens in CI secrets. |
| E – Documentation | ✅ Completed | README + architecture/env/docs updated; publishing checklist committed. | Keep docs in sync with future extras (e.g., `[ocr]` optional deps). |

## Workstream A – Packaging & Layout
1. **Flatten package namespace**
   - Move/alias `app` package to `pdf_vision_processor` to avoid collisions and convey ownership on PyPI.
   - Ensure `__init__.py` exposes useful top-level symbols (e.g., `create_app`).
2. **Project metadata**
   - Maintain a `setup.py` that defines name, description, authors, license, Python version >=3.10, classifiers, URLs, and dependencies harvested from `requirements.txt`.
   - Record `__version__ = "0.1.0"` inside `pdf_vision_processor/_version.py`, read it from `setup.py`, and increment via the helper build script.
3. **Data files**
   - Configure `include-package-data = true` plus `MANIFEST.in` entries for `pdf_vision_processor/static/**`, `pdf_vision_processor/templates/**`, and `data/sample/**` if needed for demos.
   - Audit large sample PDFs; ship only lightweight fixtures necessary for smoke tests.
4. **Runtime assets**
   - Verify relative paths inside `app.main` (static mounts) still resolve when the package is installed system-wide. Use `importlib.resources.files("pdf_vision_processor.static")` to compute absolute paths at runtime.

## Workstream B – CLI & Server Invocation
1. **Entry point definition**
   - Add a `console_scripts` entry (`pdf-vision-processor = pdf_vision_processor.cli:main`) inside `setup.py`.
   - CLI steps: load `.env` if present, parse `--host`, `--port`, `--reload`, `--log-level`, then call `uvicorn.run("pdf_vision_processor.main:app", host=host, port=port, reload=reload_flag)`.
2. **Consumer workflow**
   - Document in README:
     ```bash
     python -m venv venv && source venv/bin/activate
     pip install pdf-vision-processor
     pdf-vision-processor --host 0.0.0.0 --port 8080
     ```
   - Provide environment variable table (database URL, API keys, storage paths). When not supplied, default to SQLite under `~/.pdf-vision-processor/db.sqlite3`.
3. **Configuration resolution**
   - Implement `settings.py` that looks for:
     1. CLI flags
     2. Environment variables
     3. `config.toml` or `.env` in CWD
     4. Built-in defaults packaged with the library
   - Expose `pdf_vision_processor serve` subcommand later if multiple modes (process-once, batch) are needed.
4. **Compatibility shim**
   - Keep `run.py` delegating to `pdf_vision_processor.cli.main()` to minimize drift between repo scripts and published CLI behavior.

## Workstream C – Testing & Validation
1. **Automated tests**
   - Add smoke test that installs the package into an isolated virtualenv (or `pip install dist/*.whl`), launches `pdf-vision-processor --port 9999`, waits for `/health` response, then tears down.
   - Ensure template/static discovery works when running from outside the repo.
2. **Dependency pinning**
   - Split `dependencies` (runtime) vs `optional-dependencies.dev` (linting, pytest, mypy, black).
   - Add `uvicorn[standard]`, `fastapi`, `sqlalchemy`, `python-dotenv`, OCR/vision libs currently required.
3. **Platform coverage**
   - Document support statement (Linux/macOS). If Windows is not validated, mention limitations (e.g., file watchers or poppler dependency).

## Workstream D – Release Workflow
1. **Versioning policy**
   - Adopt SemVer. Start with `0.1.0` for the current feature set. Tag releases as `v0.1.0`. Use the build script to bump patch versions when dependencies or vendored assets change (same pattern as `shamitv/llama_cpp`).
2. **Build pipeline**
   - Script `scripts/build_dist.py` (setuptools-friendly automation akin to `build_package.py` in `shamitv/llama_cpp`):
     ```bash
     python scripts/build_dist.py  # cleans dist/, syncs assets, bumps version, runs setup.py sdist bdist_wheel
     twine check dist/*
     ```
3. **TestPyPI dry run**
   - Upload wheels to TestPyPI, install via `pip install -i https://test.pypi.org/simple pdf-vision-processor` and run CLI smoke test.
4. **Publishing**
   - Once validated, `twine upload dist/*` to PyPI (requires API token stored as env var or GitHub secret).
   - Automate via GitHub Actions: on tag push, run tests, build, upload to TestPyPI (pre-release) or PyPI (release) behind manual approval.

## Workstream E – Documentation Updates
- `README.md`: add installation section, CLI usage, configuration, troubleshooting (ports in use, missing env vars).
- `docs/architecture.md`: reference new packaging layout and resource loading strategy.
- `docs/pdf_processing.md`: link to PyPI install instructions for operators who only need the hosted API.
- `docs/plans/publishing_checklist.md` (new) enumerating pre-release QA, doc updates, version bump, and announcement steps.

## Timeline & Dependencies
1. Packaging skeleton + CLI prototype: 1 sprint.
2. Runtime asset refactor and tests: 0.5 sprint (depends on Workstream A).
3. Release automation + documentation: 0.5 sprint after CLI stabilizes.
4. Final smoke tests + TestPyPI publish: 1 week buffer for hardening.

## Risks & Mitigations
- **Static/template path issues**: mitigate by moving to `importlib.resources` helpers and cover with integration tests.
- **Large dependency footprint**: review optional ML/OCR components and gate them behind extras (e.g., `pip install pdf-vision-processor[ocr]`).
- **Secrets management for consumers**: provide `.env.example` and warn against shipping credentials; encourage use of environment variables or secret managers.
- **Operational support**: include logging defaults and instructions for pointing the CLI at production databases.
