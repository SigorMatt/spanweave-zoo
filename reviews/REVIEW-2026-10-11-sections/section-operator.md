# section-operator — the operator rehearsal at 3f06815, with the real pet project

Reviewer: lead (aux). Zoo checkout `~/git/spanweave-zoo` at `3f06815` (`## zoo...origin/zoo`, clean);
pet checkout `~/git/streaming-concierge` at `553279a`. It already held ` M MANIFEST.json`
before the run, left over from the run-2 rehearsal. It was restored at the end as asked.

**How Ctrl-C was delivered.** A driver (`scratchpad/op/drive.py`) runs terminal 1 as a real pty:
`pty.fork()` makes `uv run zoo capture …` the pty's session and foreground process group. Ctrl-C is
the byte `0x03` written to the pty master, and the kernel's line discipline then sends SIGINT to the
whole foreground group, exactly as a terminal does. Terminal 2 is a plain subprocess running in the pet checkout.

| step | typed | result |
|---|---|---|
| 1 | `uv sync --extra dev` | rc 0 |
| 2 | `make collector` | rc 0, from cache: `sha256 fcc06374… matches collector/SHA256SUMS` |
| 3 | `uv run zoo capture --project z4 --run-id 2026-10-11T17-32-31Z --kind recorded --project-manifest ~/git/streaming-concierge/MANIFEST.json` | ready in 0.61 s |
| 4 | in `~/git/streaming-concierge`: `make run-recorded ENDPOINT=http://localhost:4318` | rc 0: a 3-turn conversation with one tool call (`book_table`) |
| 5 | Ctrl-C (0x03 on the pty) | `^C`, `zoo capture: stopping`, summary, **exit 0** after 0.11 s; `pgrep otelcol-contrib`: none |
| 6 | `make verify` | **rc 0**: both the new capture and `tests/fixtures/capture` verify |
| — | `make check` | **rc 0**: 336 passed, then gates 31 passed, then verify green, then `zoo 0.0.1` (11.7 s wall) |

Terminal 1, verbatim (CR stripped):

```
zoo capture: the raw bytes are the record. Ctrl-C to stop.
zoo capture: recording POST /v1/traces on http://127.0.0.1:4318 -> captures/z4/2026-10-11T17-32-31Z/raw/
zoo capture: collector 0.162.0 re-encoding to JSON into captures/z4/2026-10-11T17-32-31Z/json/, via http://127.0.0.1:4319
  raw/0001.body  6884 bytes  sha256:f67d5be6bbd4
  json/0001.json  9543 bytes  sha256:df53d74f5e5f
^C
zoo capture: stopping
zoo capture: 1 body/bodies in raw/, 1 in json/, under captures/z4/2026-10-11T17-32-31Z/, MANIFEST.json written: kind=recorded
```

No Collector line reached the terminal. All 11 of its lines are in `collector.log`, and the shutdown line
there reads `Received signal from OS … "signal": "terminated"`: the zoo's SIGTERM. In run 2 it read
`"interrupt"`, the terminal's SIGINT.

`make verify`:

```
zoo verify: 1 capture(s) under captures/:
  captures/z4/2026-10-11T17-32-31Z: kind=recorded, 1 body/bodies in raw/, 1 in json/, 0 problem(s)
zoo verify: every recorded body still hashes to what was recorded
zoo verify: 1 capture(s) under tests/fixtures/capture/:
  tests/fixtures/capture: kind=recorded, 1 body/bodies in raw/, 1 in json/, 0 problem(s)
zoo verify: every recorded body still hashes to what was recorded
```

**What the capture holds.**
- The run directory has 10 files: `bodies.jsonl`, `collector.log`, `forwards.jsonl`,
  `json/0001.{headers.json,headers.raw,json}`, `MANIFEST.json`, `raw/0001.{body,headers.json,headers.raw}`.
- The manifest lists all 9 non-manifest files: 2 under `bodies`, 7 under `files`. It has no `problems`
  key, which means no problems. It has `forwards: [{raw/0001.body, 200}]`, `kind: recorded`, and `seal: 2d0b474d…`.
- `raw/0001.body` is 6,884 bytes, `application/x-protobuf`, uncompressed, with
  `user-agent: OTel-OTLP-Exporter-Python/1.45.1`. `json/0001.json` is 9,543 bytes.
- **The span ids are equal on both sides.** I decoded the raw protobuf with the pet's own
  `opentelemetry-proto` and compared it with the JSON re-encoding. Both give the same 5 spans in trace
  `2f236f71bffbfc1e24a01fdaabce0ce4`: root `be96a2c5d9c3c1e4 concierge.conversation` and four
  `chat stub-concierge-1` children (`adb124b73b616bd7`, `baac8244c4a1d5db`, `a9060f04109453fe`, `d4da1d522c0faeee`).
- **The project manifest is this run's own.** Its `started_at` is `2026-10-11T17:32:33.752181+00:00`.
  That falls after the capture's `started_at` (`17:32:31.712529`) and before its `ended_at` (`17:32:37.984398`).

**Where the README and the behaviour differ:** nowhere that matters for Z4. Two notes:
- **OP-1 (thread):** `collector.log` is written in the Collector's own format. It carries the operator machine's
  local UTC offset (`2026-10-11T20:32:31.616+0300`) and a random `service.instance.id` UUID. Both
  are part of a sealed, committed record once Z4 is committed. That is right by the zoo's rules (verbatim), but
  the operator should know that the timezone of the machine that took the capture will be published. The
  committed fixture shows the same thing.
- **OP-2 (thread):** README step 3 says "Wait for the one readiness line". Two more `zoo capture:` lines
  follow it at once (ports and directories). The README says so in its tee section, and SPEC §4.2 is A0c's item (4).

**Afterwards.**
- I copied the capture to `scratchpad/op/capture-copy/` as evidence, then ran
  `rm -rf captures/z4/2026-10-11T17-32-31Z` and `rmdir captures/z4 captures`.
- Zoo: `git status --short` was empty, `## zoo...origin/zoo`.
- Pet: `git -C ~/git/streaming-concierge checkout MANIFEST.json` printed "Updated 1 path from the
  index", and `git status --short` was then empty, `## main...origin/main`.

**Verdict on the operator flow:** I ran the README's six steps as the operator, with the real pet project.
**All green**: exit 0, no problems, verify 0, check 0, no Collector left running. Run 2's Z-1 is closed.
