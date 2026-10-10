# The acceptance harness. `make check` is THE gate a batch must pass before it
# counts as done (CONTRIBUTING.md, "The bar"): it wraps the exact toolchain
# commands plus the invariant gate and the capture re-hash as runnable checks.

.PHONY: check lint types test gates verify collector collector-check install-check clean

check: lint types test gates verify
	uv run zoo --version

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy --strict spanweave_zoo

test:
	uv run pytest

# The invariant gate. Its own target so a failure names the invariant that
# broke rather than "some test failed": no module under spanweave_zoo/ imports
# spanweave or spanweave_live except audit.py (CLAUDE.md section 0.6). `check`
# runs it too, via `test`; this target is how you run it alone, and how CI
# names it in a log.
gates:
	uv run pytest tests/test_gates.py -v

# Re-hash every capture against its manifest. A capture is immutable (CLAUDE.md
# section 0.6), and that claim is worth making only if something checks it on
# every run -- so this is a prerequisite of `check` and not an errand someone
# remembers.
#
# Two commands, because the first one has nothing to check here: `captures/` is
# where the zoo's own runs go and this repository holds none, so `zoo verify`
# alone says "nothing to re-hash" and exits 0 on every CI leg. The second reads
# the one real capture committed under tests/fixtures/capture/ -- one protobuf
# body through the real tee, both sides, headers and manifest -- so CI
# re-hashes bytes rather than reporting an empty tree. A named path that is not
# a capture exits 2 (SPEC.md section 5.6), so a fixture that went missing fails
# this target instead of passing quietly.
verify:
	uv run zoo verify
	uv run zoo verify tests/fixtures/capture

# Fetch the pinned stock OpenTelemetry Collector and check its sha256 against
# the release's own digest (SPEC.md section 4.1). The version lives in
# collector/VERSION and the digests in collector/SHA256SUMS; the ~100MB binary
# is gitignored, because the pin is the record and the bytes are a download.
#
# Deliberately NOT a prerequisite of anything. `make check` is green with the
# binary and without it: the integration test that runs the real Collector is
# skipped when it is absent, which is how it behaves in CI (SPEC.md section
# 4.9). A gate that reaches the network to decide whether it passes is a gate
# that fails when GitHub does.
collector:
	uv run python collector/fetch.py

# The other half of that honesty: the @needs_collector tests RAN, and not one
# of them skipped. `make check` is green with the binary and without it, which
# means `make check` alone has never once proved A2's claim anywhere but on a
# machine that happens to have run `make collector` -- a leg where all three
# tests skipped looks exactly like a leg where all three passed.
#
# So this target runs exactly those tests and FAILS if any is skipped or in
# error, and if the marker selected none of them at all (pytest exits 0 when
# everything skips, which is why it reads the junit report rather than the exit
# code). CI's sixth leg, `collector`,
# runs it right after `make collector`; locally it is how you check that the
# binary you just fetched actually re-encodes.
collector-check:
	uv run python -m tests.collector_check

# Prove that what SHIPS works: builds the sdist and the wheel, installs the
# wheel into a throwaway venv, and runs `zoo --help` from a working directory
# outside the repo -- the only gate that can catch a packaging break. It
# installs NO extras, which is also how A0-A4's independence from `spanweave`
# and `spanweave_live` is held (pyproject.toml, the `audit` extra).
#
# Deliberately not a prerequisite of `check`: it builds a wheel and a venv, and
# `check` is the fast gate a batch must pass. CI runs both.
install-check:
	uv run python -m tests.install_check

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache dist/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
