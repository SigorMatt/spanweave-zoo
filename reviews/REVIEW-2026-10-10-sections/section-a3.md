## A3 — 9074ecd (the capture is a manifest, immutable)

Cold review of exactly one commit, `9074ecd` ("manifest: a capture declares what it is,
and verify checks both directions"), batch A3.

Derived parent: `git rev-parse 9074ecd^` → **`4122152`** (`plan: A2 done, and its row's
receiver port and exporter name were wrong`). Worktrees:
`/tmp/claude-1000/-home-msi-git-spanweave/db8f7f20-b229-460c-afff-06719260f7b2/scratchpad/wt-a3`
and `…/wt-a3-parent`, both absolute, both under the scratchpad, both removed at the end.
Nothing in `/home/msi/git/spanweave-zoo` was edited, added, committed or stashed.

Environment caveat: another agent held `44318` (`LISTEN … users:(("zoo",pid=2720189))`) and
the brief says 4317–4320 are held too, so my first `zoo capture` died with
`[Errno 98] Address already in use`. I re-ran on **45318/45319/45320/45321** and everything
below is from that clean run. No test was left unrun for port reasons: the committed suite
(121 tests) passes with those ports held, because no test binds a default port. The one
place a default port got bound was *under a deliberate mutation* (see Mutation 2), and that
run failed for the right reason anyway.

---

### Hygiene

**1. Spec changed in the same commit — yes, and the §1.1 amendment is truthful.**
`SPEC.md` §5 is new, and §1.1, §2.3, §2.5, §3.1, §3.5, §4.5, §4.6 are amended in the same
commit as the code (`git show --stat 9074ecd`: `SPEC.md | 336 +++`). The §1.1 question the
brief raises — "the sink does not look at the content type except to echo it" against
`manifest.finish()` reading `content_type`/`content_encoding` out of each body's
`headers.json` — resolves in the commit's favour. §1.1 keeps the original sentence, then
localizes it rather than weakening it: *"The sentence above about the content type is about
the **sink**, and stays exactly true of it… the manifest writer copies each body's
`Content-Type` and `Content-Encoding` **across from the record it already made**… That is a
copy of what the exporter claimed, not an inspection of what it sent, and no byte of a body
is read to do it."* I verified the code matches that sentence exactly:
`spanweave_zoo/manifest.py:_declared_content` opens only
`run/<NNNN>.headers.json`, reads `document["headers"]`, and never opens the body; the
record path in `sink.py` is unchanged in this respect. The paragraph even names the A1/A3
tension it is resolving. **This is an honest amendment, not a spec bent to a shortcut.**
*Verdict: honest.*

**Finding H1 — §1.1's enumerated exception list is now one short.** §1.1 says *"Two things
are not that, and are named here rather than discovered as exceptions"* and lists the
Collector and the two `MANIFEST.json`s. `NNNN.headers.json` is now a **third** document the
zoo reads as a document (`manifest.py:_declared_content`), and it is introduced two
paragraphs *below* the list that promised to name every exception — i.e. discovered as an
exception, which is the thing the sentence disclaims. One-line fix: add it to the bullet
list. Bin: **thread**.

**2. The derived-parent run — not vacuous, and the plan's claim reproduces exactly.**
A3's tests on `4122152` (files copied into `wt-a3-parent`, `uv sync --extra dev`, real
Collector symlinked in):

```
$ uv run pytest tests/test_manifest.py -q     # in wt-a3-parent (4122152)
E       AttributeError: module 'spanweave_zoo.manifest' has no attribute 'HEADERS_SUFFIX'
19 failed in 0.28s
$ uv run pytest tests/test_capture.py -q
24 failed, 5 passed in 1.21s
```

Caveat, stated plainly: most of that red is *API-shaped*, not behavioural — the shared
fixtures die on `manifest.HEADERS_SUFFIX` and on `Capture(..., kind=…)`'s new signature, so
the parent run alone does not prove the assertions hold the behaviour. That is exactly why
§0.2 demands a mutation, and why the hand reproduction matters. By hand on `4122152`, over
a real capture copied in:

```
# the plan's claim (i): an unlisted body on disk
$ printf 'not a recorded body' > …/z4/real-01/raw/0003.body
$ uv run zoo verify …/parent-captures
  …/z4/real-01: 3 body/bodies, 0 problem(s)
zoo verify: every recorded body still hashes to what was recorded
EXIT=0

# the plan's claim (ii): verify of one run directory
$ uv run zoo verify …/parent-captures/z4/real-01
zoo verify: no captures under …/z4/real-01/ -- nothing to re-hash
EXIT=0

# control: the changed byte already failed at the parent (A1)
$ printf '\x41' | dd of=…/raw/0001.body bs=1 seek=20 count=1 conv=notrunc
$ uv run zoo verify …/parent-captures
  ! …: raw/0001.body sha256 is 49c3627b…, MANIFEST.json says abb3460e…
EXIT=1
```

Both exit codes the plan's §4 note claims (**0** and **0**, now **1** and **1**) reproduced
verbatim. The control matters for how the headline claim should be read: leg (i) of it was
already true at A1, and **only (ii)/(iii) are A3's new behaviour.**
*Verdict: the parent run is genuinely informative for the two new behaviours, weakly
informative (API-shaped red) for the rest.*

**3. Mutations — three applied in `wt-a3`, each shown caught, each reverted.**

*Mutation 1 — `verify` ignores an unlisted body.* `manifest.problems()`'s last line
`return found + _unlisted(run, document)` → `return found`:
```
FAILED tests/test_manifest.py::test_a_body_on_disk_that_the_manifest_does_not_list_fails_verify
FAILED tests/test_manifest.py::test_a_listed_body_dropped_from_the_manifest_fails_verify
FAILED tests/test_manifest.py::test_a_headers_file_whose_body_is_not_listed_fails_verify
3 failed, 45 passed in 1.16s
```
and by hand the mutant re-greens the real corrupt capture (`unlisted-body EXIT=0`).

*Mutation 2 — `kind` becomes optional.* `manifest.label`'s `if kind not in KINDS: raise` →
`if False:`, and `cli.py`'s `--kind` from `required=True, choices=…` to
`default="recorded"`:
```
FAILED tests/test_manifest.py::test_a_capture_cannot_be_labelled_with_a_kind_the_spec_does_not_name[] (+4 params)
FAILED tests/test_capture.py::test_the_capture_command_requires_a_kind
FAILED tests/test_capture.py::test_the_capture_command_refuses_a_kind_the_spec_does_not_name
7 failed, 41 passed in 1.38s
```

*Mutation 3 — `verify` compares the wrong digest* (hash `<NNNN>.headers.json` instead of
the body, in `manifest.problems`):
```
FAILED tests/test_manifest.py::test_the_manifest_carries_every_field_section_5_names
FAILED tests/test_manifest.py::test_verify_of_one_run_directory_re_hashes_that_run
FAILED tests/test_capture.py::test_the_capture_ends_by_writing_every_field_the_manifest_carries
FAILED tests/test_sink.py::test_verify_passes_on_a_capture_the_sink_wrote
8 failed, 60 passed in 1.68s
```
After each revert: `git diff --stat` empty, `121 passed in 2.72s`.
*Verdict: the new tests hold the behaviour, not merely run.*

**4. No clock, no randomness, no network outside the injected seams — verified.**
```
$ grep -rnE "time\.time|datetime\.now|datetime\.utcnow|time\.monotonic|random|uuid|socket\.|requests|httpx|urllib|http\.client|time\.sleep" spanweave_zoo/ --include="*.py"
spanweave_zoo/cli.py:70:    return datetime.now(UTC).isoformat()          # _system_clock, the one seam
spanweave_zoo/cli.py:80:    time.sleep(seconds)                           # _system_sleep (SPEC §4.8)
spanweave_zoo/forward.py:32:import http.client                            # the tee's forward (SPEC §4.3)
spanweave_zoo/collector.py:216:  probe = socket.create_connection(        # readiness probe (SPEC §4.8)
```
Nothing else; `random`/`uuid`/`hash()` appear nowhere. `manifest.py` imports only
`hashlib, json, threading, Callable, dataclass, Path, Any` — **no `time`, no `datetime`**.
`started_at`/`ended_at` come from the injected clock and from nowhere else:
`capture.py:184 started_at=self._now()` and `capture.py:279
manifest.finish(self.run, ended_at=self._now())`, where `self._now = now` (`capture.py:116`)
is the constructor argument `cli.py` fills with `_system_clock`. `tests/test_capture.py`
drives a counting fake (`Clock.__call__` → `2026-10-09T12:00:{ticks:02d}+00:00`) and asserts
`document[STARTED_AT] == "2026-10-09T12:00:01+00:00"` — a value the test chose.
*Verdict: holds.*

**Finding H2 — the no-clock invariant has no gate, unlike the import rule.**
`tests/test_gates.py` holds exactly one invariant (no `spanweave`/`spanweave_live` import
outside `audit.py`). CLAUDE.md's "Architecture invariants" and CONTRIBUTING's bar both state
"no clock, no randomness, no socket outside an injected seam" with the same force, and that
one is held by review only. Not A3's debt (A0's), and A3 does not breach it — registering it
because every later batch widens the surface. Bin: **thread**.

**5. One concern, and the CHANGELOG.** `CHANGELOG.md` has an `## A3 — the capture is a
manifest, immutable` section with six bullets, all `SPEC.md`-cited. The commit subject is
`<area>: <one line>` and the body names A3 and every SPEC section touched. `make install-check`
green (`install-check: OK -- what ships works`), and `tests/install_check.py` grew only
A3-shaped assertions (the shipped `zoo capture` refuses with no `--kind`/`--project-manifest`).

**Finding H3 — the second defect is a second concern, folded in rather than split.**
The sink's "already holds a body" glob fix (`sink.py`: `*`+suffix counted
`0001.headers.json` as a body in the json sink) is `SPEC.md` §3.1 / A1 territory, not §5, and
it arrived with its own spec amendment and two tests. CONTRIBUTING is explicit: *"A drive-by
fix noticed on the way is a second commit, or a line in `OPEN_QUESTIONS.md`."* It was noticed
on the way — while exercising A3's own README section — and folded in. Mitigating: the commit
body names it in its own paragraph, WORKPLAN §4 records it, the fix is six lines, and A2 set
the same precedent with its `SIGINT` fix. So: a **real but minor deviation** kept reviewable
by honest disclosure. The actionable part is the inconsistency, not this commit: either
CONTRIBUTING should say "a defect the batch's own exercise surfaces may land in the batch
commit, named in the body", or batches should split it. Bin: **thread**.

**Finding H4 — the README does not match the row the orchestrator corrected.** WORKPLAN's
A3 row now reads *"**four typed commands and a `Ctrl-C`**, in two terminals (the row said
'five', which holds only by counting the keystroke)"*, and `README.md` still opens the
section with *"**Five commands, in two terminals.**"* and numbers `Ctrl-C` as command 4 of
5. The corrected acceptance criterion and the artifact disagree. Bin: **thread**.

*Hygiene verdict: the bar is cleared — spec in the same commit and honestly amended, a
derived-parent run that is informative for the new behaviour, three mutations caught, the
seams intact, a CHANGELOG entry — with one real one-concern deviation (H3) and three doc
nits (H1, H2, H4).*

---

### Claim: verify fails on a changed byte, an unlisted body, a missing manifest entry

Exercised for real in `wt-a3`, not read off the tests. A genuine capture first: `zoo capture
--project z4 --run-id real-01 --kind real --project-manifest … --port 45318 --json-port 45319
--collector-port 45320 --collector-grpc-port 45321`, two hand-built OTLP protobuf POSTs
(`tests/otlp.py`), stopped with `kill -INT` the way the README says:

```
zoo capture: collector 0.162.0 up, re-encoding to JSON
  raw/0001.body  128 bytes  sha256:abb3460ed377
  raw/0002.body  128 bytes  sha256:abb3460ed377
  json/0001.json  763 bytes  sha256:8dfd53e0b114
zoo capture: 3 body/bodies under …/z4/real-01/, MANIFEST.json written: kind=real
capture exit=0
```
The real Collector ran; `MANIFEST.json` carries every §5 field, with
`content_type: "application/x-protobuf"` on the raw bodies and `"application/json"` on the
json one, both carried across from their `headers.json`. Baseline `zoo verify` EXIT=0.

**(i) one byte flipped with `dd`, not a rewrite — fails, and un-fails on restore.**
```
$ xxd -s 20 -l 1 raw/0001.body          → 00000014: 12
$ printf '\x41' | dd of=…/raw/0001.body bs=1 seek=20 count=1 conv=notrunc
$ xxd -s 20 -l 1 raw/0001.body          → 00000014: 41   (size still 128)
$ uv run zoo verify …/z4/real-01
  ! …/z4/real-01: raw/0001.body sha256 is 49c3627b78869f00…, MANIFEST.json says abb3460ed377…
zoo verify: 1 problem(s). A capture is immutable (CLAUDE.md section 0.6): these bytes are not
            the bytes that were recorded.
EXIT=1
$ printf '\x12' | dd … ; uv run zoo verify …   →  EXIT=0
```
Message names the file, both digests and the invariant. Note the length check is an `elif`
after the digest check (`manifest.py:problems`), which is fine — a length change implies a
digest change — so you never see both lines for one body.

**(ii) a body on disk that no entry lists — fails.**
```
$ printf 'not a recorded body' > …/z4/real-01/raw/0003.body
$ uv run zoo verify …/z4/real-01
  ! …: raw/0003.body is on disk but absent from MANIFEST.json -- nothing recorded it, so
       nothing says what it should hash to
EXIT=1
```
A non-body stray (`stray.txt` at the run root) is caught by the same line, EXIT=1.

**(iii) one `bodies` entry removed, the file left on disk — fails, with two lines.**
```
$ # drop the raw/0002.body entry from MANIFEST.json, leave both files
$ uv run zoo verify …/z4/real-01
  …/z4/real-01: kind=real, 2 body/bodies, 2 problem(s)
  ! …: raw/0002.body is on disk but absent from MANIFEST.json -- nothing recorded it, …
  ! …: raw/0002.headers.json is on disk but no body of its own is listed in MANIFEST.json
EXIT=1
```

**Are (ii) and (iii) two cases or one check seen twice?** **One check, two entry points.**
Both land in `manifest.py:_unlisted` and are decided by the same predicate — `if name not in
listed` — reached either by adding a file (ii) or by removing the entry that listed it (iii);
there is no separate "missing manifest entry" code path. The brief lists them separately, and
as *operator scenarios* they are different (a file arriving from somewhere else vs. a manifest
that was edited); as *coverage* they are the same assertion, and `tests/test_manifest.py`'s
`test_a_body_on_disk_that_the_manifest_does_not_list_fails_verify` and
`test_a_listed_body_dropped_from_the_manifest_fails_verify` both die to Mutation 1, which is
the proof they share a mechanism. The one thing (iii) exercises that (ii) does not is the
*headers* branch (`raw/0002.headers.json` with no listed body) — and that has its own test and
its own message. So: a distinction with a small difference, worth keeping in the fixtures,
not worth counting as two checks.

**`make check` runs it, and the dependency is live.** `Makefile:7` is
`check: lint types test gates verify` and `Makefile:36-37` is `verify:` /
`uv run zoo verify`. Proved by making verify fail and running the whole gate:
```
$ cp -a <the real capture> captures/z4/real-01 && make verify     → EXIT=0 (green)
$ printf '\x41' | dd of=captures/z4/real-01/raw/0001.body bs=1 seek=20 count=1 conv=notrunc
$ make check
… 30 passed in 0.06s        (gates)
uv run zoo verify
  ! captures/z4/real-01: raw/0001.body sha256 is 49c3627b…, MANIFEST.json says abb3460e…
make: *** [Makefile:37: verify] Error 1
MAKE_CHECK_EXIT=2
```
With the capture honest again, `make check` → EXIT=0; with no captures at all, `make check` →
EXIT=0 (`zoo verify: no captures under captures/ -- nothing to re-hash`). `.gitignore` says
*"`captures/` is deliberately NOT ignored: a capture is the record"*, so once a real capture is
committed, CI re-hashes it on every push. Today the repository holds none, so the verify step
in CI is a no-op — the claim "`make check` runs it" is true; "`make check` re-checks the
captures' bytes" becomes true with the first committed capture.

*Verdict: the claim holds in full and I verified all three legs by hand, with the caveats that
(ii) and (iii) are one check reached two ways, leg (i) already worked at A1, and the gate is
live but has nothing to chew on until a capture is committed.*

---

### Unlisted cases probed

All against the real `real-01` capture in `wt-a3`, one at a time, restored between each.

| case | exit | message |
|---|---|---|
| listed body **missing from disk** | **1** | `raw/0002.body is listed in MANIFEST.json but missing` |
| `MANIFEST.json` **absent** (run dir, `raw/` present) | **1** | `no readable MANIFEST.json -- nothing records what this capture's bodies should hash to` (and `kind=none declared`) |
| `MANIFEST.json` **not valid JSON** (`{ this is not json`) | **1** | `MANIFEST.json cannot be read: Expecting property name enclosed in double quotes: line 1 column 3 (char 2)` |
| valid JSON but **not an object** (`[1,2,3]`) | **1** | `MANIFEST.json cannot be read: MANIFEST.json is not a JSON object` |
| object with **no `bodies` list** | **1** | `MANIFEST.json cannot be read: MANIFEST.json has no 'bodies' list` |
| **unknown `kind`** in the manifest (`"simulated"`) | **0** | `kind=simulated, 3 body/bodies, 0 problem(s)` — printed, not judged |
| **`kind` absent** | **0** | `kind=none declared, 3 body/bodies, 0 problem(s)` |
| `zoo capture --kind simulated` (the write path) | **2** | `zoo capture: error: argument --kind: invalid choice: 'simulated' (choose from 'real', 'recorded')` |
| stray `NNNN.headers.json` with no body | **1** | `raw/0009.headers.json is on disk but no body of its own is listed in MANIFEST.json` |
| leftover `MANIFEST.json.partial` | **1** | `MANIFEST.json.partial is on disk but absent from MANIFEST.json` |
| empty subdirectory in the run | **0** | clean — directories are not files, correctly ignored |

No traceback anywhere: every refusal is a printed line plus a non-zero exit. The `kind` row is
per `SPEC.md` §5.6 ("prints each run's `kind` as the capture declares it"), so it is specified
rather than an oversight — but see A3-2.

**Finding A3-1 — a mistyped path still exits 0, which is the very failure mode A3 fixed.**
*blocks run 2.* `zoo verify <path that is not a run and not a root>` prints "no captures" and
exits **0**:
```
$ uv run zoo verify …/a3/captures/z4/typo-run-id
zoo verify: no captures under …/z4/typo-run-id/ -- nothing to re-hash
EXIT=0
$ mkdir -p …/captures/z9/half/json && printf '{}' > …/z9/half/json/0001.json
$ uv run zoo verify …/captures/z9/half            # a half-capture: json/ but no MANIFEST, no raw/
zoo verify: no captures under …/z9/half/ -- nothing to re-hash
EXIT=0
$ uv run zoo verify …/captures                    # the same directory, found from the root
  ! …/z9/half: no readable MANIFEST.json -- nothing records what this capture's bodies should hash to
EXIT=1
```
`cli.py:83-92 _is_run` recognizes a run by `MANIFEST.json` *or* `raw/` being present, and
`cli.py:95-106 _run_directories` returns `[]` for anything else — including a path that does
not exist. The README tells the operator to type exactly `uv run zoo verify
captures/z4/<run-id>`, so a fat-fingered run id, or a capture whose raw sink never started,
answers "nothing to re-hash" and exits green. A3's own commit body says it fixed *"one run
directory, which used to glob two levels down from it, find nothing and exit zero"* — the fix
covers the directories `_is_run` recognizes and leaves the same reassuring pass for the rest.
`cli.py:24-29` even claims the opposite of the code: *"a path that looks like nothing is not a
tree that verified -- saying so with a non-zero exit is the one failure mode this command
exists to prevent."* It is not said so; it exits 0. Smallest honest fix: a `[path]` the
operator typed that is neither a run nor a root containing runs is a non-zero refusal, and the
"nothing to re-hash is not a failure" exemption stays for the **default** `captures/` only
(`SPEC.md` §5.6's last line, which is about a tree with no captures, not about a typo).
I verified all three outputs above.

**Finding A3-2 — `verify` guarantees the bodies and nothing else in the capture.**
*next batch.* Three edits, each a capture being edited, each verifying green:
```
$ rm …/z4/real-01/raw/0001.headers.json          # the headers of a LISTED body
  …/z4/real-01: kind=real, 3 body/bodies, 0 problem(s)                       EXIT=0
$ printf '{"headers": [["Content-Type", "text/plain"]]}' > …/raw/0001.headers.json
  …/z4/real-01: kind=real, 3 body/bodies, 0 problem(s)                       EXIT=0
$ # kind real→recorded, project_manifest replaced, started_at set to 1999
  …/z4/real-01: kind=recorded, 3 body/bodies, 0 problem(s)                   EXIT=0
```
`manifest.py:_unlisted` checks headers→body but never body→headers, and nothing hashes a
headers file or any manifest field but `bodies`. Strictly, CLAUDE.md §0.6 rule 2 only promises
"a sha256 of each **body** in the manifest", and `SPEC.md` §5.7 says "What is durable is the
**bytes** of a capture" — so this is within the letter of the spec. It is outside the letter of
§5.6's "**both directions**" and of §2.3's "the headers are part of the capture", and it
matters concretely for A5: §5.2 says *"The audit reads this field as the truth about which it
was… which is exactly why a guess here would be a lie there"*, and a hand-edited `kind`
verifies green. The cheap half is symmetry — a listed body whose `headers.json` is missing is a
problem line, exactly as the reverse already is. The expensive half (a digest over the headers
files, or a manifest self-digest) is a spec decision, not a patch. I verified the three exit
codes; I did **not** attempt a fix.

**Finding A3-3 — a capture that failed to start is left labelled, and verifies green as
`kind=real` with zero bodies.** *thread.* My port-contention run is the reproduction:
`zoo capture` exited **2** with `refusing to start: [Errno 98] Address already in use`, and
left behind:
```json
{"bodies": [], "collector_version": "0.162.0",
 "ended_at": "2026-10-09T22:24:37.878026+00:00", "kind": "real",
 "project_manifest": {…}, "sink_version": "0.0.1",
 "started_at": "2026-10-09T22:24:37.624771+00:00"}
```
and `zoo verify` over the root reports `…/z4/review-a3: kind=real, 0 body/bodies, 0
problem(s)` — green. `capture.py:start()` labels the manifest (line 179) *before* the json
listener, the Collector and the raw listener bind, so any bind failure after labelling leaves a
complete-looking empty capture; `stop()` then adds `ended_at` through `_finish`. SPEC §5.5's
promise is narrower than this reads — *"a capture that never got as far as a labelled manifest
is left with nothing written at all"* — and it is kept, but the operator-visible outcome is a
directory the audit will later count as a `real` capture that recorded nothing. Worth one line
in §5.5 and/or leaving nothing behind when `start()` unwinds before a body could arrive.

**Finding A3-4 — `MANIFEST.json.partial` is reported as an unlisted file.** *thread.*
`manifest.write_json` writes `MANIFEST.json.partial` then `replace()`s it, and
`_unlisted`'s `rglob("*")` has no exemption for it, so a `zoo verify` racing a live capture can
report `MANIFEST.json.partial is on disk but absent from MANIFEST.json` and exit 1 on a capture
that is fine (reproduced by leaving the file in place: EXIT=1). The window is small and
reporting a genuine crashed-write leftover is arguably right, but the message would send an
operator looking for a body that does not exist. One line in `_unlisted`, or a name that is not
inside the run directory.

*Verdict: verify refuses honestly and never crashes on everything the brief named and on six
things nobody named — but two gaps are real: a typed path it does not recognize still exits 0
(A3-1, the one that blocks run 2), and its "both directions" cover body bytes only, so an
edited `kind` or headers file passes (A3-2).*

---

### Caveats

- Ports 4317–4320 were held by another agent and 44318 by a third; everything was run on
  45318–45321. The committed suite needs none of those: `121 passed in 2.88s` in `wt-a3`
  (3 real-Collector tests included, via a symlink to the repo's gitignored
  `collector/otelcol-contrib`), and `make check`, `make verify` and `make install-check` are
  all green. Nothing was left unrun for port reasons.
- `make demo`-style live runs, CI legs and anything needing a network or an API key were not
  attempted; the §4 note's CI-green-on-five-legs claim is unverified here.
- Both worktrees were removed with `git worktree remove --force <absolute path>` after the run.
