"""`zoo audit`: a capture through the libraries it was taken for (`SPEC.md` §7).

The one module under `spanweave_zoo/` that imports `spanweave`,
`spanweave_live` and `agentgolden`, and the gate's exemption is this **path**
(`tests/gates.py`). `cli.py` imports it only when `zoo audit` runs, so nothing
else the zoo does needs the `audit` extra (`SPEC.md` §7.1).

Five steps (`SPEC.md` §7.3): the exporter's bytes into `spanweave-live serve`;
the Collector's JSON into `serve` three times -- once completed by its end of
input, then under `--quiet 0` and `--root-grace 0` with the captured gaps
slept (B6a);
each written graph against `spanweave.build` of the same records; `spanweave
inspect`, the graph's diagnostics and one row per node; `agentgolden`'s
signature as a smoke.
What comes out is a report, `audit/<project>-<run-id>.md`, whose findings each
name the repository that owns them (`SPEC.md` §7.4). Nothing here repairs,
retries or works around anything: a finding is a reproduction, never a fix
(`CLAUDE.md` §0.6 rule 7).

**The audit parses no payload of its own** (`SPEC.md` §1.1). A body is read
by `serve`, or in-process by the pinned receiver's own `Endpoint`, and a graph
only through spanweave's public API. The one document read here with `json` is
the zoo's own `json/NNNN.headers.json` -- for the method, the path and three
headers, so that the in-process `Endpoint` is handed the request `serve` was.

`serve` is a child process of this interpreter on a port the kernel chooses;
the capture reaches it through the zoo's own replayer and its `send` seam
(`SPEC.md` §6.2). The child's command is a parameter, so a test can hand the
audit a `serve` that never starts.
"""

from __future__ import annotations

import dataclasses
import importlib.metadata
import json
import queue
import subprocess
import sys
import tempfile
import threading
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

import spanweave
from agentgolden.signature import signature as agentgolden_signature
from spanweave.adapters import classify
from spanweave_live import Endpoint
from spanweave_live import Request as LiveRequest
from spanweave_live.routing import trace_id_of

from spanweave_zoo import __version__, manifest, replay

# The three libraries the `audit` extra pins, as (distribution, module).
LIBRARIES = (
    ("spanweave", "spanweave"),
    ("spanweave-live", "spanweave_live"),
    ("agentgolden", "agentgolden"),
)
OWNERS = tuple(distribution for distribution, _ in LIBRARIES)
SPANWEAVE, SPANWEAVE_LIVE, AGENTGOLDEN = OWNERS

# The children, run by this interpreter so they are the pinned code and no
# other: `python -m spanweave_live.cli` is `spanweave-live`, and
# `python -m spanweave.cli` is `spanweave`.
SERVE_COMMAND: tuple[str, ...] = (sys.executable, "-m", "spanweave_live.cli")
INSPECT_COMMAND: tuple[str, ...] = (sys.executable, "-m", "spanweave.cli")

# Where `serve` writes, relative to its own working directory, so the paths in
# its events are the same on every run.
GRAPHS = "graphs"

# Bounds, in seconds, on a child that does not do what it should. A bound
# passed is an incomplete step, never a finding (`SPEC.md` §7.5).
START_WAIT = 30.0
FINISH_WAIT = 60.0
SEND_TIMEOUT = 10.0

LISTENING = "listening"
FINISHED = "finished"
UNMAPPED = "unmapped_attributes"
ORPHAN_PARENT = "orphan_parent"

# Step 2's two policy runs (`SPEC.md` §7.3, B6a), in the order they run: each
# flag at zero, the audit's value -- the pinned receiver documents no default
# (`OPEN_QUESTIONS.md` §8).
POLICIES: tuple[tuple[str, str], ...] = (("--quiet", "0"), ("--root-grace", "0"))

# The receiver's events a policy run tables, and the one that resets a trace's
# generation count (`SPEC.md` §7.3).
COMPLETED = "completed"
LATE_ARRIVAL = "late_arrival"
WRITTEN = "written"
RELEASED = "released"
FORGOTTEN = "forgotten"
TABLED = (COMPLETED, LATE_ARRIVAL, WRITTEN, RELEASED)

# The key OTLP's span carries its events under, kept verbatim on the record
# spanweave's reader flattens (`SPEC.md` §7.3, step 4).
EVENTS = "events"

INSTALL = "uv sync --extra dev --extra audit"


class AuditRefused(Exception):
    """Nothing was audited and no report written: exit 2 (`SPEC.md` §7.2)."""


# --- the pins (SPEC.md section 7.2) -------------------------------------------


@dataclass(frozen=True, slots=True)
class Pin:
    distribution: str
    version: str
    pinned: str
    installed: str


def pinned_shas() -> dict[str, str]:
    """The sha each of the three is pinned at, from the zoo's own metadata.

    The `audit` extra's `Requires-Dist` lines, `name @ git+URL@sha ; extra ==
    'audit'` -- which is `pyproject.toml` as the installed zoo carries it.
    """
    pinned: dict[str, str] = {}
    for requirement in importlib.metadata.requires("spanweave-zoo") or []:
        spec, _, marker = requirement.partition(";")
        if "audit" not in marker:
            continue
        name, _, url = spec.partition(" @ ")
        if url:
            pinned[name.strip()] = url.strip().rsplit("@", 1)[-1]
    return pinned


def installed_sha(distribution: str) -> str | None:
    """The commit the installed distribution was built from (PEP 610)."""
    try:
        text = importlib.metadata.distribution(distribution).read_text(
            "direct_url.json"
        )
    except importlib.metadata.PackageNotFoundError:
        return None
    if text is None:
        return None
    try:
        document = json.loads(text)
    except ValueError:
        return None
    commit = document.get("vcs_info", {}).get("commit_id")
    return commit if isinstance(commit, str) else None


def pins(installed: Callable[[str], str | None] = installed_sha) -> list[Pin]:
    """The three pins, each checked against what is installed. Refuses on any
    difference: a finding cites a sha, and a sha the run did not use would make
    it irreproducible."""
    pinned = pinned_shas()
    found: list[Pin] = []
    for distribution, _ in LIBRARIES:
        sha = pinned.get(distribution)
        if sha is None:
            raise AuditRefused(
                f"the installed zoo's `audit` extra pins no {distribution}; "
                f"reinstall it ({INSTALL})"
            )
        actual = installed(distribution)
        if actual != sha:
            raise AuditRefused(
                f"{distribution} is pinned at {sha} and the installed one is "
                f"{actual or 'of no readable commit'}; a finding must cite the "
                f"commit that ran ({INSTALL})"
            )
        found.append(
            Pin(distribution, importlib.metadata.version(distribution), sha, actual)
        )
    return found


# --- what a run of `serve` left behind ------------------------------------------


@dataclass(slots=True)
class Served:
    """One `spanweave-live serve` run with a replay into it (steps 1 and 2)."""

    source: str
    files: list[str]
    command: list[str]
    outcomes: list[replay.Outcome] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    policy: tuple[str, ...] = ()
    """The completion flags given to `serve` (`--quiet 0`), or none: end of
    input alone. A run with one is replayed with `--timing`."""
    replayed: list[str] = field(default_factory=list)
    """The replayer's own lines (`SPEC.md` §6.4), verbatim."""
    exit: int | None = None
    graphs: dict[str, bytes] = field(default_factory=dict)
    problem: str | None = None

    def events(self) -> Iterator[tuple[str, dict[str, Any] | None]]:
        """Every stderr line, with its JSON object or `None` if it is not one."""
        for line in self.lines:
            try:
                document = json.loads(line)
            except ValueError:
                yield line, None
                continue
            yield line, document if isinstance(document, dict) else None

    def finished(self) -> dict[str, Any] | None:
        for _, event in self.events():
            if event is not None and event.get("code") == FINISHED:
                return event
        return None

    @property
    def label(self) -> str:
        """`step 2`'s run named by its flags: `--quiet 0`, or `end of input`."""
        return " ".join(self.policy) or "end of input"

    @property
    def timed(self) -> bool:
        return bool(self.policy)


class _Lines:
    """A child's stream, drained by a thread into a list and a queue."""

    def __init__(self, stream: IO[bytes]) -> None:
        self.lines: list[str] = []
        self.arrived: queue.Queue[str | None] = queue.Queue()
        self._stream = stream
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self) -> None:
        for raw in self._stream:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            self.lines.append(line)
            self.arrived.put(line)
        self.arrived.put(None)

    def join(self) -> None:
        self._thread.join(timeout=FINISH_WAIT)
        self._stream.close()


def _port(lines: _Lines) -> tuple[int | None, str | None]:
    """The port `serve` says it bound, or why there is none."""
    while True:
        try:
            line = lines.arrived.get(timeout=START_WAIT)
        except queue.Empty:
            return None, f"serve wrote no `{LISTENING}` event in {START_WAIT:g}s"
        if line is None:
            return None, f"serve exited before its `{LISTENING}` event"
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("code") == LISTENING:
            port = event.get("port")
            if isinstance(port, int):
                return port, None


def serve(
    run: Path,
    source: str,
    workdir: Path,
    command: Sequence[str],
    *,
    policy: tuple[str, ...] = (),
    sleep: Callable[[float], None] | None = None,
) -> Served:
    """Start `serve [policy] --requests N`, replay one side of `run` into it,
    collect. With a policy the replay is `--timing`, sleeping through `sleep`
    (`SPEC.md` §6.3, §7.3)."""
    files = replay.planned(run, source)
    here = workdir / (
        source + "".join(f"{flag}{value}" for flag, value in _pairs(policy))
    )
    here.mkdir(parents=True)
    argv = [
        *command,
        "serve",
        "--port",
        "0",
        "--out",
        GRAPHS,
        *policy,
        "--requests",
        str(len(files)),
    ]
    served = Served(source=source, files=files, command=argv, policy=policy)
    try:
        process = subprocess.Popen(
            argv,
            cwd=here,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        # A command that cannot be executed at all: the step is incomplete
        # and the report is still written (`SPEC.md` section 7.5).
        served.problem = f"serve did not start: {type(error).__name__}: {error}"
        return served
    assert process.stderr is not None
    lines = _Lines(process.stderr)
    port, problem = _port(lines)
    if port is not None:
        served.outcomes = replay.replay(
            run,
            source=source,
            send=replay.sender("127.0.0.1", port, timeout=SEND_TIMEOUT),
            timing=served.timed,
            sleep=sleep if served.timed else None,
            log=served.replayed.append,
        )
        unsent = [o.file for o in served.outcomes if o.status is None]
        if unsent:
            problem = (
                f"{len(unsent)} of {len(files)} {source}/ bodies were not sent "
                f"({', '.join(unsent)}), so serve, waiting for {len(files)} "
                f"requests, was stopped"
            )
            process.kill()
    try:
        served.exit = process.wait(timeout=FINISH_WAIT)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=FINISH_WAIT)
        problem = problem or f"serve did not finish within {FINISH_WAIT:g}s"
    if problem is not None and served.exit is not None and port is None:
        problem = f"{problem} (exit {served.exit})"
    lines.join()
    served.lines = lines.lines
    served.problem = problem
    graphs = here / GRAPHS
    if graphs.is_dir():
        served.graphs = {
            path.name: path.read_bytes() for path in sorted(graphs.glob("*.json"))
        }
    return served


def _pairs(policy: Sequence[str]) -> list[tuple[str, str]]:
    return list(zip(policy[::2], policy[1::2], strict=True))


@dataclass(frozen=True, slots=True)
class PolicyEvent:
    """One row of a policy run's table (`SPEC.md` §7.3, step 2)."""

    code: str
    trace_id: str
    index: object
    generation: int
    reason: str


def policy_events(served: Served) -> list[PolicyEvent]:
    """Every `completed`, `late_arrival`, `written` and `released` event, in
    the order `serve` wrote them, with the generation counted from the
    receiver's own events (they carry none): a trace's nth `completed` is
    generation n, a `late_arrival` opens the next, `written` and `released`
    belong to the one just completed, and `forgotten` starts the count again.
    """
    done: dict[str, int] = {}
    rows: list[PolicyEvent] = []
    for _, event in served.events():
        if event is None:
            continue
        code, trace_id = event.get("code"), event.get("trace_id")
        if not isinstance(trace_id, str):
            continue
        if code == FORGOTTEN:
            done[trace_id] = 0
            continue
        if code not in TABLED:
            continue
        detail = str(event.get("detail", ""))
        reason = detail
        if code == COMPLETED:
            done[trace_id] = done.get(trace_id, 0) + 1
            generation = done[trace_id]
            reason = detail.split(":", 1)[0]
        elif code == LATE_ARRIVAL:
            generation = done.get(trace_id, 0) + 1
            reason = ""
        else:
            generation = done.get(trace_id, 0)
        rows.append(
            PolicyEvent(
                code=str(code),
                trace_id=trace_id,
                index=event.get("index"),
                generation=generation,
                reason=reason,
            )
        )
    return rows


# --- step 3: the records the receiver fed ---------------------------------------


@dataclass(slots=True)
class Partition:
    """One trace's records, as the pinned receiver partitions them, and the
    three serializations of its graph (`SPEC.md` §7.3)."""

    trace_id: str | None
    origins: list[str] = field(default_factory=list)
    feed: list[Any] = field(default_factory=list)
    live: bytes | None = None
    batch: bytes | None = None
    batch_error: str | None = None
    incremental: bytes | None = None
    incremental_error: str | None = None
    graph: spanweave.Graph | None = None
    inspect_exit: int | None = None
    inspect_output: str = ""
    signature_steps: list[str] | None = None
    signature_error: str | None = None

    @property
    def records(self) -> int:
        return len(self.feed)

    @property
    def name(self) -> str:
        return "(no trace id)" if self.trace_id is None else self.trace_id

    @property
    def file(self) -> str:
        return f"{self.trace_id}.json"


@dataclass(slots=True)
class Reread:
    """What the in-process receiver made of the `json/` bodies."""

    statuses: list[int] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    unclaimed: list[str] = field(default_factory=list)


def _first(headers: object, name: str) -> str | None:
    if not isinstance(headers, list):
        return None
    for pair in headers:
        if (
            isinstance(pair, list)
            and len(pair) == 2
            and isinstance(pair[0], str)
            and isinstance(pair[1], str)
            and pair[0].lower() == name
        ):
            return pair[1]
    return None


def _request(run: Path, file: str) -> LiveRequest:
    """`file` as the request `serve` received: the zoo's own parse of its head
    (`SPEC.md` §2.3) and the body's bytes, untouched."""
    body = Path(file)
    parsed = json.loads(
        (run / body.with_name(body.stem + manifest.HEADERS_SUFFIX)).read_text(
            encoding="utf-8"
        )
    )
    headers = parsed.get("headers")
    return LiveRequest(
        method=str(parsed.get("method", "")),
        target=str(parsed.get("path", "")),
        body=(run / file).read_bytes(),
        content_type=_first(headers, "content-type"),
        content_encoding=_first(headers, "content-encoding"),
        transfer_encoding=_first(headers, "transfer-encoding"),
    )


def reread(run: Path, files: Sequence[str]) -> Reread:
    """Every `json/` body through the pinned `Endpoint`, in receipt order, and
    every record it read partitioned by the pinned `trace_id_of`."""
    endpoint = Endpoint()
    found = Reread()
    by_trace: dict[str | None, Partition] = {}
    for file in files:
        exchange = endpoint.handle(_request(run, file))
        found.statuses.append(exchange.response.status)
        for position, record in enumerate(exchange.records.records, start=1):
            origin = f"{file} record {position}"
            trace_id = trace_id_of(record)
            if trace_id not in by_trace:
                by_trace[trace_id] = Partition(trace_id)
            by_trace[trace_id].feed.append(record)
            by_trace[trace_id].origins.append(origin)
            if not classify(record):
                found.unclaimed.append(origin)
    identified = [p for key, p in by_trace.items() if key is not None]
    found.partitions = identified + ([by_trace[None]] if None in by_trace else [])
    return found


def _refusal(error: Exception) -> str:
    code = getattr(error, "code", None)
    named = f" (code {code})" if isinstance(code, str) else ""
    return f"{type(error).__name__}{named}: {error}"


def compare(partition: Partition) -> None:
    """Build the partition's batch and incremental graphs (`SPEC.md` §7.3)."""
    lines = b"".join(
        json.dumps(record).encode("utf-8") + b"\n" for record in partition.feed
    )
    try:
        batch = spanweave.build(lines)
        assert batch.meta is not None
        undigested = dataclasses.replace(
            batch, meta=dataclasses.replace(batch.meta, source_digest=None)
        )
        partition.batch = spanweave.dumps(undigested)
    except spanweave.SpanweaveError as error:
        partition.batch_error = _refusal(error)
    builder = spanweave.Builder()
    try:
        for record in partition.feed:
            builder.feed(record)
        graph = builder.graph()
        partition.graph = graph
        partition.incremental = spanweave.dumps(graph)
    except spanweave.SpanweaveError as error:
        partition.incremental_error = _refusal(error)


def divergence_owner(
    live: bytes | None, batch: bytes | None, incremental: bytes | None
) -> str | None:
    """Who owns a live graph that is not the batch graph (`SPEC.md` §7.4).

    `None` when all three agree. spanweave when its own two builds disagree or
    either raised -- prefix consistency is its §10.1 -- and spanweave-live
    when spanweave's two agree and the file `serve` wrote does not.
    """
    if batch is None or incremental is None or batch != incremental:
        return SPANWEAVE
    if live != batch:
        return SPANWEAVE_LIVE
    return None


# --- steps 4 and 5 ------------------------------------------------------------


def inspect(partition: Partition, workdir: Path, command: Sequence[str]) -> None:
    """`spanweave inspect graphs/<trace_id>.json`, its output verbatim."""
    done = subprocess.run(
        [*command, "inspect", f"{GRAPHS}/{partition.file}"],
        cwd=workdir / replay.JSON,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=FINISH_WAIT,
        check=False,
    )
    partition.inspect_exit = done.returncode
    output = done.stdout.decode("utf-8", "replace")
    errors = done.stderr.decode("utf-8", "replace")
    partition.inspect_output = output + (f"\n[stderr]\n{errors}" if errors else "")


def smoke(
    partition: Partition, signature: Callable[[spanweave.Graph], Any]
) -> str | None:
    """`signature(graph)`, no rules. Returns the owner of a raise, if any."""
    graph = partition.graph
    if graph is None:
        return None
    try:
        computed = signature(graph)
    except Exception as error:
        partition.signature_error = f"{type(error).__name__}: {error}"
        malformed = spanweave.validate(spanweave.to_document(graph))
        return SPANWEAVE if malformed else AGENTGOLDEN
    partition.signature_steps = [str(step.token) for step in computed.steps]
    return None


# --- findings and the report --------------------------------------------------


@dataclass(frozen=True, slots=True)
class Finding:
    """A reproduction (`SPEC.md` §7.4): never a fix."""

    step: int
    owner: str
    title: str
    capture: str
    commands: tuple[str, ...]
    observed: str
    expected: str


@dataclass(slots=True)
class Audit:
    path: Path
    findings: list[Finding] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)
    partitions: list[Partition] = field(default_factory=list)
    policy_runs: list[Served] = field(default_factory=list)

    @property
    def exit(self) -> int:
        return 1 if self.incomplete else 0


def _serve_commands(run: Path, served: Served) -> tuple[str, ...]:
    flag = "--raw" if served.source == replay.RAW else "--json"
    policy = "".join(f" {part}" for part in served.policy)
    timing = " --timing" if served.timed else ""
    return (
        f"uv run spanweave-live serve --port <port> --out {GRAPHS}{policy} "
        f"--requests {len(served.files)}",
        f"uv run zoo replay {run} --to http://127.0.0.1:<port> {flag}{timing}",
    )


def _endpoint_events(served: Served) -> dict[int, list[str]]:
    """Each request's endpoint events, by its 1-based arrival index."""
    by_index: dict[int, list[str]] = {}
    for _, event in served.events():
        if event is None or event.get("layer") != "endpoint":
            continue
        index = event.get("index")
        if isinstance(index, int):
            by_index.setdefault(index, []).append(
                f"`{event.get('code')}`: {event.get('detail')}"
            )
    return by_index


def serve_findings(step: int, run: Path, served: Served) -> list[Finding]:
    found: list[Finding] = []
    commands = _serve_commands(run, served)
    by_status: dict[int, list[int]] = {}
    for position, outcome in enumerate(served.outcomes, start=1):
        if outcome.status is not None and not outcome.delivered:
            by_status.setdefault(outcome.status, []).append(position)
    events = _endpoint_events(served)
    for status, positions in sorted(by_status.items()):
        observed = "\n".join(
            f"- `{served.files[p - 1]}`: {status}; "
            + ("; ".join(events.get(p, [])) or "no endpoint event")
            for p in positions
        )
        found.append(
            Finding(
                step=step,
                owner=SPANWEAVE_LIVE,
                title=(
                    f"{len(positions)} of {len(served.files)} "
                    f"{served.source}/ bodies answered {status}"
                ),
                capture=str(run),
                commands=commands,
                observed=observed,
                expected=(
                    "2xx: each body is the export as it was recorded, unmodified "
                    "(`zoo verify` passed before the audit ran)"
                ),
            )
        )
    if served.exit not in (None, 0):
        found.append(
            Finding(
                step=step,
                owner=SPANWEAVE_LIVE,
                title=f"serve exited {served.exit}",
                capture=str(run),
                commands=commands,
                observed=f"exit status {served.exit}",
                expected="exit 0: the input ended and everything was delivered",
            )
        )
    loose = [line for line, event in served.events() if event is None]
    if loose:
        found.append(
            Finding(
                step=step,
                owner=SPANWEAVE_LIVE,
                title=f"{len(loose)} stderr line(s) that are not one JSON object",
                capture=str(run),
                commands=commands,
                observed="\n".join(f"- `{line}`" for line in loose),
                expected="every event line is one JSON object (its SPEC §8.3)",
            )
        )
    return found


def partition_findings(
    run: Path, served: Served, found: Reread, routed: object
) -> list[Finding]:
    """Step 3's findings (`SPEC.md` §7.4)."""
    findings: list[Finding] = []
    commands = _serve_commands(run, served)
    if found.unclaimed:
        findings.append(
            Finding(
                step=3,
                owner=SPANWEAVE,
                title=f"{len(found.unclaimed)} record(s) no adapter claims",
                capture=str(run),
                commands=(
                    *commands,
                    "spanweave.adapters.classify(record) for each record "
                    "spanweave_live.Endpoint reads from the body",
                ),
                observed="\n".join(
                    f"- {origin}: `classify` returned `()`"
                    for origin in found.unclaimed
                ),
                expected=(
                    "an adapter claims each record of an OTLP export "
                    "`read_records` unpacked, so its trace id can be had "
                    "through the adapter surface"
                ),
            )
        )
    for partition in found.partitions:
        if partition.trace_id is None:
            findings.append(
                Finding(
                    step=3,
                    owner=SPANWEAVE_LIVE,
                    title=(
                        f"{partition.records} record(s) serve routed reached no "
                        f"graph it wrote, and no event names them"
                    ),
                    capture=str(run),
                    commands=commands,
                    observed=(
                        "\n".join(f"- {origin}" for origin in partition.origins)
                        + f"\n\nRouted to the no-trace builder; `finished` "
                        f"reports `routed: {routed}`, and the graphs serve "
                        f"wrote hold "
                        f"{sum(p.records for p in found.partitions if p.trace_id)}"
                        f" of them."
                    ),
                    expected=(
                        "each record of a trace reaches that trace's graph, or "
                        "an event says where it went. spanweave-live's SPEC "
                        "§4.3, §5.4 and §8.5 at the pinned sha send a record with no "
                        "trace id through the adapter surface to the no-trace "
                        "builder, which is never completed and never written"
                    ),
                )
            )
            continue
        if partition.live is None:
            findings.append(
                Finding(
                    step=3,
                    owner=SPANWEAVE_LIVE,
                    title=f"no graph written for trace {partition.trace_id}",
                    capture=str(run),
                    commands=commands,
                    observed=f"{GRAPHS}/{partition.file} is absent",
                    expected="every trace held at end of input is written",
                )
            )
            continue
        owner = divergence_owner(partition.live, partition.batch, partition.incremental)
        if owner is not None:
            findings.append(
                Finding(
                    step=3,
                    owner=owner,
                    title=f"live and batch graphs differ for {partition.trace_id}",
                    capture=str(run),
                    commands=(
                        *commands,
                        f"spanweave.build(<the {partition.records} records as "
                        f"JSON lines>), meta.source_digest removed",
                    ),
                    observed=(
                        f"live {_size(partition.live)}, batch "
                        f"{_size(partition.batch, partition.batch_error)}, "
                        f"incremental "
                        f"{_size(partition.incremental, partition.incremental_error)}"
                    ),
                    expected=(
                        "all three byte-identical (spanweave SPEC §10.1, "
                        "prefix consistency)"
                    ),
                )
            )
    explained = {p.file for p in found.partitions if p.trace_id is not None}
    for name in sorted(set(served.graphs) - explained):
        findings.append(
            Finding(
                step=3,
                owner=SPANWEAVE_LIVE,
                title=f"a written graph no partition explains: {name}",
                capture=str(run),
                commands=commands,
                observed=f"{GRAPHS}/{name} was written",
                expected="one file per trace the receiver's records name",
            )
        )
    return findings


def _size(data: bytes | None, error: str | None = None) -> str:
    if data is None:
        return f"raised {error}" if error else "absent"
    return f"{len(data)} bytes"


def unmapped(graph: spanweave.Graph) -> tuple[list[tuple[str, int]], int]:
    """The keys `unmapped_attributes` names, by how many diagnostics name each,
    and the bytes those diagnostics take as compact sorted JSON."""
    keys: Counter[str] = Counter()
    for diagnostic in graph.diagnostics:
        if diagnostic.code == UNMAPPED and isinstance(diagnostic.source, list):
            keys.update(str(key) for key in diagnostic.source)
    document = spanweave.to_document(graph)
    size = sum(
        len(
            json.dumps(
                item, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        )
        for item in document.get("diagnostics", [])
        if isinstance(item, dict) and item.get("code") == UNMAPPED
    )
    return sorted(keys.items(), key=lambda pair: (-pair[1], pair[0])), size


def _model(node: spanweave.Node) -> str:
    model = node.attributes.get("model")
    return "absent" if model is None else f"`{_cell(model)}`"


def _parent(graph: spanweave.Graph, node: spanweave.Node, orphans: set[str]) -> str:
    if graph.parents(node.id, spanweave.EdgeKind.PARENT):
        return "yes"
    return "absent from graph" if node.id in orphans else "no"


def _span_events(node: spanweave.Node) -> object | None:
    """The record's `events`, as it carries them, or `None` for no such key."""
    source = node.raw.source
    if isinstance(source, dict) and EVENTS in source:
        carried: object = source[EVENTS]
        return carried
    return None


def node_table(graph: spanweave.Graph) -> list[str]:
    """Step 4's row per node (`SPEC.md` §7.3), then each node's span events
    as its record carries them, as compact sorted JSON."""
    on: dict[str, Counter[str]] = {}
    for diagnostic in graph.diagnostics:
        if diagnostic.node_id is not None:
            on.setdefault(diagnostic.node_id, Counter())[diagnostic.code] += 1
    orphans = {n for n, codes in on.items() if codes.get(ORPHAN_PARENT)}
    lines = [
        "| Node | Kind | Status | Model | Parent | Diagnostics | Span events |",
        "|---|---|---|---|---|---|---|",
    ]
    carried: list[tuple[str, object]] = []
    for node in graph.nodes():
        codes = ", ".join(
            f"`{code}`" + (f" x{count}" if count > 1 else "")
            for code, count in sorted(on.get(node.id, Counter()).items())
        )
        events = _span_events(node)
        if events is None:
            shown = "absent"
        else:
            carried.append((node.id, events))
            shown = str(len(events)) if isinstance(events, list) else "1 value"
        lines.append(
            f"| `{_cell(node.id)}` | {node.kind.value} | {node.status.value} | "
            f"{_model(node)} | {_parent(graph, node, orphans)} | "
            f"{codes or 'none'} | {shown} |"
        )
    lines.append("")
    if carried:
        lines.extend(["Span events, as each record carries them:", ""])
        for node_id, events in carried:
            lines.extend(
                [
                    f"`{node_id}`:",
                    "",
                    "```json",
                    json.dumps(
                        events,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                    "```",
                    "",
                ]
            )
    return lines


class Writer:
    """The report, line by line."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, *lines: str) -> None:
        self.lines.extend(lines)

    def block(self, text: str, language: str = "") -> None:
        self(f"```{language}", *(text.splitlines() or [""]), "```", "")

    def text(self) -> str:
        return "\n".join(self.lines).rstrip("\n") + "\n"


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _policy_run(
    w: Writer,
    run: Path,
    result: Audit,
    policy: tuple[str, str],
    not_run: dict[int, str],
) -> None:
    """One of step 2's policy runs (`SPEC.md` §7.3)."""
    w(f"### Step 2 under `{' '.join(policy)}`, replayed `--timing`", "")
    served = next((s for s in result.policy_runs if s.policy == policy), None)
    if served is None:
        w(f"Not run: {not_run.get(2, 'step 2 was not run')}.", "")
        return
    w.block("\n".join(_serve_commands(run, served)), "bash")
    w("| Body | Status | Gap slept before it |", "|---|---|---|")
    for outcome in served.outcomes:
        slept = "none" if outcome.slept is None else f"{outcome.slept:g}s"
        w(f"| `{outcome.file}` | {outcome.status or _cell(outcome.error)} | {slept} |")
    w("", f"serve exit status: {served.exit}", "")
    if served.problem:
        w(f"Incomplete: {served.problem}", "")
    notes = [line.strip() for line in served.replayed if line.lstrip().startswith("!")]
    if notes:
        w("The replayer's notes:", "", *(f"- {_cell(n)}" for n in notes), "")
    rows = policy_events(served)
    w("| Event | Trace | Index | Generation | Reason |", "|---|---|---|---|---|")
    for row in rows:
        w(
            f"| `{row.code}` | `{_cell(row.trace_id)}` | {_cell(row.index)} | "
            f"{row.generation} | {_cell(row.reason)} |"
        )
    if not rows:
        w("| (none) | | | | |")
    finished = served.finished()
    w(
        "",
        "`finished`: "
        + ("none" if finished is None else f"`{json.dumps(finished, sort_keys=True)}`"),
        "",
    )
    w("Every event serve wrote to stderr, verbatim:", "")
    w.block("\n".join(served.lines) or "(none)", "json")


def render(
    run: Path,
    pinned: list[Pin],
    steps: dict[int, Served | None],
    found: Reread | None,
    result: Audit,
    not_run: dict[int, str],
) -> str:
    document = manifest.read(run)
    w = Writer()
    w(f"# Audit: `{run}`", "")
    w(
        "Written by `zoo audit` (`SPEC.md` §7). Every finding below is a "
        "reproduction and names the repository that owns it; nothing here is "
        "a fix.",
        "",
    )
    w("| | |", "|---|---|")
    w(f"| capture | `{run}` |")
    w(f"| kind | `{document.get('kind')}` |")
    w(f"| seal | `{document.get('seal')}` |")
    w(f"| collector | `{document.get('collector_version')}` |")
    w(f"| zoo | `{__version__}` |", "")
    w("| Library | Version | Pinned sha | Installed sha |", "|---|---|---|---|")
    for pin in pinned:
        w(f"| {pin.distribution} | {pin.version} | {pin.pinned} | {pin.installed} |")
    w("")

    w("## Method", "")
    w(
        "1. `zoo replay --raw` into `spanweave-live serve`: every status, every "
        "event, the exit status.",
        "2. `zoo replay --json` into `serve`. Completion is `serve --requests "
        "N`: after the Nth request the input has ended, and the end of input "
        "runs spanweave-live's `Run.finish()`, which replaces the completion "
        "with `Cap(0)` and ticks once, so every trace still held completes "
        "and is written (its SPEC §8.5 at the pinned sha). That is the "
        "`Cap(0)`-at-end the plan names, chosen by the receiver's CLI and not "
        "by the audit. Step 2 then runs twice more, each `serve` given one "
        "completion policy as well as `--requests N` and each replay "
        "`--timing`, the captured gaps slept: `--quiet 0`, then "
        "`--root-grace 0`. **The zeros are the audit's values**: the pinned "
        'receiver documents no default for either flag (its README, "The '
        'CLI"), so the audit chooses the smallest legal value, at which each '
        "policy fires at the first tick its condition holds (its SPEC §5.3); "
        "a trace neither completed by the Nth request completes at end of "
        "input by `Cap(0)`, and each `completed` event's reason says which. "
        "Step 3 compares the end-of-input run's graphs; the two policy runs "
        "are an observation and yield no finding.",
        "3. Each `json/` body re-read in-process by the pinned "
        "`spanweave_live.Endpoint`, each record partitioned by the pinned "
        "`trace_id_of`; per partition, the live file against "
        "`spanweave.build` of its records as JSON lines (`meta.source_digest` "
        "removed, spanweave SPEC §10.4) and against a `spanweave.Builder` fed "
        "them in order.",
        "4. `spanweave inspect` on each written graph, verbatim; diagnostics by "
        "code, `unmapped_attributes` keys by size, `unknown` nodes; one row per "
        "node -- kind, status, model, whether its parent is present, the "
        "diagnostics naming it, and its span events as the record carries them.",
        "5. `agentgolden.signature.signature(graph)`, no rules.",
        "",
        "Steps 4 and 5 read the `Builder`'s graph (spanweave has no public "
        "reader from a graph document back to a `Graph`); step 3 compares its "
        "bytes with the live file's. The `listening` port and the clock "
        "readings in a `completed` or `late_arrival` event (`seconds`, and the "
        "two in its `detail`) are the receiver's and differ run to run; nothing "
        "else in this report does.",
        "",
    )

    w("## Findings", "")
    counts = Counter(f.owner for f in result.findings)
    w(
        f"{len(result.findings)} finding(s): "
        + ", ".join(f"{owner} {counts.get(owner, 0)}" for owner in OWNERS)
        + ".",
        "",
    )
    if result.incomplete:
        w("**Incomplete** -- a step could not be completed:", "")
        w(*(f"- {reason}" for reason in result.incomplete), "")
    for number, finding in enumerate(result.findings, start=1):
        w(f"### F{number}. {finding.title} -- owner: {finding.owner}", "")
        w(f"Step {finding.step}. Capture: `{finding.capture}`", "")
        w("Command:", "")
        w.block("\n".join(finding.commands), "bash")
        w("Observed:", "", finding.observed, "")
        w("Expected:", "", finding.expected, "")

    for number, title in ((1, "the exporter's bytes"), (2, "the Collector's JSON")):
        w(f"## Step {number} -- {title} into `spanweave-live serve`", "")
        served = steps.get(number)
        if served is None:
            w(f"Not run: {not_run.get(number, 'no body on this side')}.", "")
            continue
        w.block("\n".join(_serve_commands(run, served)), "bash")
        w("| Body | Status |", "|---|---|")
        for outcome in served.outcomes:
            w(f"| `{outcome.file}` | {outcome.status or _cell(outcome.error)} |")
        w("", f"serve exit status: {served.exit}", "")
        if served.problem:
            w(f"Incomplete: {served.problem}", "")
        if number == 2:
            w(
                "Graphs written: "
                + (", ".join(f"`{GRAPHS}/{n}`" for n in served.graphs) or "none"),
                "",
            )
        w("Every event serve wrote to stderr, verbatim:", "")
        w.block("\n".join(served.lines) or "(none)", "json")
        if number == 2:
            for flag, value in POLICIES:
                _policy_run(w, run, result, (flag, value), not_run)

    w("## Step 3 -- live against batch", "")
    if found is None:
        w(f"Not run: {not_run.get(3, 'step 2 did not complete')}.", "")
    else:
        w(
            "| Trace | Records | Live | Batch | Incremental | Result |",
            "|---|---|---|---|---|---|",
        )
        for p in found.partitions:
            if p.trace_id is None:
                verdict = "no-trace builder: never written"
            elif p.live is None:
                verdict = "no live file"
            else:
                owner = divergence_owner(p.live, p.batch, p.incremental)
                verdict = "equal" if owner is None else f"differs ({owner})"
            w(
                f"| `{p.name}` | {p.records} | {_size(p.live)} | "
                f"{_cell(_size(p.batch, p.batch_error))} | "
                f"{_cell(_size(p.incremental, p.incremental_error))} | {verdict} |"
            )
        w("")
        for p in found.partitions:
            w(f"Records of `{p.name}`, in the order fed:", "")
            w(*(f"- {origin}" for origin in p.origins), "")

    w("## Step 4 -- `spanweave inspect`", "")
    graphs = [p for p in (found.partitions if found else []) if p.live is not None]
    if not graphs:
        w(f"Not run: {not_run.get(4, 'no graph was written')}.", "")
    for p in graphs:
        w(f"### `{p.name}`", "")
        w.block(f"uv run spanweave inspect {GRAPHS}/{p.file}", "bash")
        w(f"Exit status {p.inspect_exit}:", "")
        w.block(p.inspect_output or "(no output)")
        if p.graph is None:
            w("No `Graph` to read: the `Builder` raised.", "")
            continue
        if p.live != p.incremental:
            w("The live file and the `Builder`'s graph differ; read: the latter.", "")
        codes = Counter(d.code for d in p.graph.diagnostics)
        w("| Diagnostic | Count |", "|---|---|")
        w(*(f"| `{code}` | {count} |" for code, count in sorted(codes.items())))
        w("")
        keys, size = unmapped(p.graph)
        w(
            f"`{UNMAPPED}`: {codes.get(UNMAPPED, 0)} diagnostic(s), {size} bytes "
            f"as compact sorted JSON.",
            "",
        )
        if keys:
            w("| Unmapped key | Diagnostics naming it |", "|---|---|")
            w(*(f"| `{_cell(key)}` | {count} |" for key, count in keys), "")
        unknown = Counter(
            node.name for node in p.graph.nodes(spanweave.NodeKind.UNKNOWN)
        )
        w(
            f"`unknown` nodes: {sum(unknown.values())}"
            + (
                " -- "
                + ", ".join(f"`{_cell(n)}` x{c}" for n, c in sorted(unknown.items()))
                if unknown
                else ""
            )
            + ".",
            "",
        )
        w(*node_table(p.graph))

    w("## Step 5 -- `agentgolden` signature", "")
    if not graphs:
        w(f"Not run: {not_run.get(5, 'no graph was written')}.", "")
    else:
        w("| Trace | Result |", "|---|---|")
        for p in graphs:
            if p.signature_error is not None:
                shown = f"raised {_cell(p.signature_error)}"
            elif p.signature_steps is None:
                shown = "not run: no `Graph`"
            else:
                shown = f"{len(p.signature_steps)} step(s): " + _cell(
                    ", ".join(f"`{t}`" for t in p.signature_steps)
                )
            w(f"| `{p.name}` | {shown} |")
        w("")
    return w.text()


# --- the command -------------------------------------------------------------


def report_path(run: Path, out: Path) -> Path:
    return out / f"{run.parent.name}-{run.name}.md"


def audit(
    run: Path,
    *,
    out: Path,
    serve_command: Sequence[str] = SERVE_COMMAND,
    inspect_command: Sequence[str] = INSPECT_COMMAND,
    signature: Callable[[spanweave.Graph], Any] = agentgolden_signature,
    installed: Callable[[str], str | None] = installed_sha,
    reread: Callable[[Path, Sequence[str]], Reread] = reread,
    sleep: Callable[[float], None],
) -> Audit:
    """Audit one run and write its report. Raises `AuditRefused` (exit 2).

    `sleep` has no default: it is the one way the audit waits on the real
    clock, step 2's two timed replays (`SPEC.md` §7.6), and `cli.py` passes
    the real one as it does to `zoo replay --timing`.
    """
    if not (run / manifest.MANIFEST_NAME).is_file():
        raise AuditRefused(
            f"{run} is not a run directory: it holds no {manifest.MANIFEST_NAME}"
        )
    problems = manifest.problems(run)
    if problems:
        raise AuditRefused(
            f"{run} does not verify ({len(problems)} problem(s), first: "
            f"{problems[0]}); run `zoo verify {run}`"
        )
    pinned = pins(installed)
    result = Audit(path=report_path(run, out))
    steps: dict[int, Served | None] = {}
    not_run: dict[int, str] = {}
    found: Reread | None = None
    routed: object = None
    with tempfile.TemporaryDirectory(prefix="zoo-audit-") as scratch:
        workdir = Path(scratch)
        for number, source in ((1, replay.RAW), (2, replay.JSON)):
            try:
                served = serve(run, source, workdir, serve_command)
            except replay.ReplayRefused as refused:
                steps[number] = None
                not_run[number] = str(refused)
                result.incomplete.append(f"step {number} not run: {refused}")
                continue
            steps[number] = served
            if served.problem is not None:
                result.incomplete.append(f"step {number}: {served.problem}")
            else:
                result.findings.extend(serve_findings(number, run, served))
            if number != 2:
                continue
            # The two policy runs (`SPEC.md` section 7.3): an observation, no
            # finding of their own; one that could not be completed is an
            # incomplete step, and step 3 still reads the run above.
            for policy in POLICIES:
                timed = serve(
                    run, source, workdir, serve_command, policy=policy, sleep=sleep
                )
                result.policy_runs.append(timed)
                if timed.problem is not None:
                    result.incomplete.append(f"step 2 ({timed.label}): {timed.problem}")
        json_side = steps.get(2)
        if json_side is None or json_side.problem is not None:
            reason = "step 2 did not complete"
            for number in (3, 4, 5):
                not_run[number] = reason
        else:
            found = reread(run, json_side.files)
            answered = [o.status for o in json_side.outcomes]
            finished = json_side.finished()
            routed = None if finished is None else finished.get("routed")
            fed = sum(p.records for p in found.partitions)
            if found.statuses != answered or routed != fed:
                # The reconstruction vouches for nothing built from it: no
                # partition is compared and steps 4 and 5 are not run
                # (`SPEC.md` section 7.3).
                mismatch = (
                    f"the in-process re-read does not match serve "
                    f"(statuses {found.statuses} against {answered}; "
                    f"{fed} records against routed {routed})"
                )
                result.incomplete.append(f"step 3: {mismatch}")
                not_run[3] = mismatch
                not_run[4] = not_run[5] = "step 3 did not complete"
                found = None
        if found is not None and json_side is not None:
            for partition in found.partitions:
                if partition.trace_id is not None:
                    partition.live = json_side.graphs.get(partition.file)
                compare(partition)
            result.findings.extend(partition_findings(run, json_side, found, routed))
            for partition in found.partitions:
                if partition.live is None:
                    continue
                inspect(partition, workdir, inspect_command)
                commands = (f"uv run spanweave inspect {GRAPHS}/{partition.file}",)
                if partition.inspect_exit != 0:
                    result.findings.append(
                        Finding(
                            step=4,
                            owner=SPANWEAVE,
                            title=(
                                f"spanweave inspect exited "
                                f"{partition.inspect_exit} on {partition.file}"
                            ),
                            capture=str(run),
                            commands=(*_serve_commands(run, json_side), *commands),
                            observed=partition.inspect_output,
                            expected="exit 0 on a graph spanweave wrote",
                        )
                    )
                owner = smoke(partition, signature)
                if owner is not None:
                    result.findings.append(
                        Finding(
                            step=5,
                            owner=owner,
                            title=f"signature(graph) raised on {partition.file}",
                            capture=str(run),
                            commands=(
                                *_serve_commands(run, json_side),
                                "agentgolden.signature.signature(graph)",
                            ),
                            observed=str(partition.signature_error),
                            expected=(
                                "a Signature, on a graph spanweave built "
                                + (
                                    "(spanweave.validate finds it malformed)"
                                    if owner == SPANWEAVE
                                    else "(spanweave.validate finds it well-formed)"
                                )
                            ),
                        )
                    )
            result.partitions = found.partitions
        text = render(run, pinned, steps, found, result, not_run)
    out.mkdir(parents=True, exist_ok=True)
    result.path.write_text(text, encoding="utf-8")
    return result
