# Publishing Checklist

A repeatable set of steps for releasing `pdf-vision-processor` to TestPyPI/PyPI.

## Pre-flight
- [ ] Ensure `main` is green and your feature branch is merged.
- [ ] Bump `__version__` in `pdf_vision_processor/__init__.py` or use `python scripts/build_dist.py --bump <patch|minor|major>`.
- [ ] Update `CHANGELOG`/release notes (if applicable) and confirm `README.md` plus docs reference the new functionality.
- [ ] Run the test suite (`pytest`) and a manual smoke test against `pdf-vision-processor --port 9999`.
- [ ] Verify `data/sample/` only contains lightweight fixtures.

## Build & Validate Artifacts
- [ ] `python -m venv .venv && source .venv/bin/activate` (or reuse an existing environment).
- [ ] `pip install -r requirements.txt && pip install -r <dev-deps>` to ensure tooling (pytest, build, twine) is present.
- [ ] `python scripts/build_dist.py --bump patch` (omit `--bump` if already versioned).
- [ ] Inspect `dist/` for both `.tar.gz` and `.whl` files and run `twine check dist/*` (handled automatically by the script unless `--skip-twine` is passed).

## TestPyPI Dry Run
- [ ] `python -m twine upload --repository testpypi dist/*` using a TestPyPI token.
- [ ] In a clean virtualenv, install the candidate build via `pip install -i https://test.pypi.org/simple pdf-vision-processor`.
- [ ] Run `pdf-vision-processor --port 9999 --reload` and hit `/health` or `/` to confirm assets load correctly.

## Production Publish
- [ ] Tag the commit (`git tag vX.Y.Z && git push --tags`).
- [ ] `python -m twine upload dist/*` with your PyPI token/credentials.
- [ ] Announce the release (Slack/Teams/email) with highlights and upgrade guidance.
- [ ] Open a follow-up issue for any deferred documentation or automation tasks.
