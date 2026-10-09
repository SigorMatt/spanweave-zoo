# Changelog

Pre-release. Nothing here is frozen: the CLI, the capture layout and
`MANIFEST.json` all still move. Entries are by batch id (`WORKPLAN.md` §1).

## A1 — the sink records bytes, and nothing else

- `zoo sink --port 4318 --out captures/<project>/<run-id>/raw` (`SPEC.md` §3),
  on stdlib `http.server` and **no new dependency**: a `POST /v1/traces` with
  any `Content-Type` and any `Content-Encoding` becomes `raw/NNNN.body` -- the
  bytes exactly as received, still gzipped if they arrived gzipped -- beside
  `raw/NNNN.headers.json` (method, path, **every** header as a list of
  `[name, value]` pairs so a repeated header survives, body length, and a
  receipt time from the injected `now`). Answered `200`, empty body, the
  request's own content type echoed back.
- A POST to any other path is answered `404` and **still recorded**, under
  `rejected/` with its own counter (`SPEC.md` §3.4). An exporter aimed at the
  wrong endpoint is a fact to hold, and a 404 that dropped the bytes would
  lose it.
- The sink never decodes, decompresses, parses or validates a body, and never
  edits a capture: it **refuses to start** if `--out` already holds a body
  (`SPEC.md` §3.1). A body that is empty, truncated, mislabelled or lying
  about its encoding is recorded like any other; a POST with no
  `Content-Length` is recorded as a zero-byte body rather than having its
  framing guessed at (`SPEC.md` §3.7).
- `MANIFEST.json`'s `bodies` entries -- `file`, `sha256`, `bytes` -- written
  incrementally as the sink records (`SPEC.md` §3.5). This is the one part of
  the manifest `CLAUDE.md` §0.6 rule 2 already mandated, and `zoo verify` had
  nothing to re-hash against without it. The digest has exactly one home: it
  is **not** also copied into `NNNN.headers.json`. Everything else the
  manifest will carry is still A3's, added to this same file and these same
  entries (`SPEC.md` §5, which now also records what A1 did *not* do: fail on
  a body present on disk but absent from the manifest).
- `zoo verify` therefore stops refusing every capture and re-hashes: non-zero
  on a changed byte, a wrong length, a listed body that is missing, or a
  manifest it cannot read. A run with no readable manifest is still a refusal.
- Seams, all injected and all named in `SPEC.md` §3.6: `now` (the one real
  clock in the package lives in `cli.py`), the listener factory (tests bind
  `127.0.0.1` on port `0`, so the suite cannot collide with a port in use),
  and `before_record` / `after_record` -- which is how the receipt-order test
  holds two POSTs genuinely in flight **without sleeping**.
- Twenty new tests over a real socket, plus one in `tests/test_cli.py`
  asserting that no module but `cli.py` reads a clock: a protobuf, a JSON and
  a gzip body each round-tripping byte for byte; two POSTs in flight numbered
  in receipt order; `zoo verify` passing on a sink-written capture and failing
  after one bit of one byte changes. Mutation shown caught: a sink that
  decompresses before writing fails the gzip case.

## A0 — the repository skeleton

- `pyproject.toml`: package `spanweave_zoo`, console script `zoo`, Python
  3.11–3.14, **zero runtime dependencies**, the PEP 561 marker shipped. An
  `audit` extra — and only an extra — pins `spanweave` and `spanweave-live` by
  git sha for A5; a `dev` extra carries ruff, mypy and pytest. `uv.lock`
  committed.
- `Makefile` as the source of truth for the gates: `check` (ruff, ruff format,
  `mypy --strict`, pytest, the gate, `zoo verify`), `verify`, `install-check`.
  `zoo verify` is a prerequisite of `check` from the start, because "a capture
  is immutable" is only a claim if something re-checks it on every run
  (`CLAUDE.md` §0.6 rule 2).
- `.github/workflows/ci.yml`: `make check` and `make install-check` on Python
  3.11–3.14 on ubuntu-latest and 3.12 on macos-latest. CI installs
  `--extra dev` and never `--extra audit`: A0 through A4 must work without
  `spanweave` and `spanweave_live` present, and a CI that installed them would
  hide the day that stopped being true.
- `CLAUDE.md`: the operating contract, carrying `WORKPLAN.md` §0.6 as its own
  §0.6 — the eight standing rules, the architecture invariants, the halt
  points.
- `CONTRIBUTING.md`: the batch bar — spec first, a failing test confirmed red
  on the *derived* parent `<sha>^` in a worktree created by absolute path under
  the scratchpad, one named mutation shown caught, one concern per commit, a
  changelog entry, `make check` and `make verify` green, CI green on the tip.
- `SPEC.md` §1 (the zoo parses nothing, fixes nothing, improves nothing) and §2
  (the capture layout on disk). §§3–7 are headings naming what A1–A5 will
  specify, deliberately empty.
- `tests/gates.py` + `tests/test_gates.py`: one gate — no module under
  `spanweave_zoo/` imports `spanweave` or `spanweave_live` except `audit.py`.
  An AST walk, not a grep, so a nested, aliased or `TYPE_CHECKING` import is
  caught too; thirteen planted violations are each watched failing, and each is
  watched passing inside `audit.py`.
- `spanweave_zoo/`: `__init__.py`, `cli.py` and `py.typed`, minimal on purpose.
  `zoo --help`, `zoo --version`, and `zoo verify`, which exits 0 on a tree with
  no captures and **fails** on a capture it cannot yet re-hash rather than
  reporting an unchecked capture as verified — A3 implements the re-hash
  (`SPEC.md` §5).
- `README.md`: what the zoo is, the pre-release warning, the gates, and the
  provenance of the contract and the briefs.
- `EXPORT-CONTRACT.md` and `ZOO-BRIEFS.md` at the root, byte-identical to the
  documents handed to the pet projects, with their sha256s in `README.md`.
  Both root copies are contract version **1.1**; the pilot project Z4
  (`streaming-concierge`) was built against **1.0**, and the difference is the
  contract's own closing "Changes from 1.0" section. From now on every project
  is started from these bytes.
