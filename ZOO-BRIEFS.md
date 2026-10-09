# Pet project briefs — six agents, six telemetry shapes

Each brief is given to its implementer together with `EXPORT-CONTRACT.md`
and nothing else. A brief says what the agent does and which packages
instrument it. It never says what the telemetry should look like.

Implementers pin exact versions of every package they name; the versions
below are "current at time of writing" and are theirs to confirm.

---

## Z1 — `ledger-clerk`: deep nesting under OpenInference / LangChain

**Framework and instrumentation.** LangChain (LCEL + a tool-calling agent),
instrumented by `openinference-instrumentation-langchain`, exported by the
stock OpenTelemetry SDK.

**What it does.** A bookkeeping assistant answers "reconcile this month"
over a small CSV ledger. The top-level agent delegates to a *sub-chain* that
delegates to a *second* sub-chain: agent → `categorize` chain → `lookup_rate`
chain → tool `fx_rate(date, currency)` → LLM `summarize`. Five levels of
parent/child at least, with a tool call at the deepest level and an LLM call
on the way back up.

**Scenario, fixed.** One ledger of 12 lines; three categories; two
currencies. The recorded stub returns the same categorization and the same
summary every run.

**Why this shape.** Nesting depth and parent-before-child ordering in a real
exporter's batches.

---

## Z2 — `fan-out-researcher`: parallel tool calls under OpenInference / LlamaIndex

**Framework and instrumentation.** LlamaIndex (a `FunctionAgent` or the
workflow API) with `openinference-instrumentation-llama-index`.

**What it does.** A research assistant answers "compare the three vendors'
return policies" by calling a `fetch_policy(vendor)` tool for all three
vendors **concurrently** (the framework's async tool execution; make the tool
`async` and have it `await asyncio.sleep` a different small duration per
vendor so they finish out of request order), then one LLM call to compare.

**Scenario, fixed.** Three vendors; three canned policy texts; sleeps of
0.30 s, 0.10 s, 0.20 s.

**Why this shape.** Sibling spans that start together and end in a different
order from the one they were requested in; a parent that ends after all of
them.

---

## Z3 — `echo-planner`: a long history-resending loop under the OpenAI Agents SDK

**Framework and instrumentation.** The OpenAI Agents SDK, instrumented by
`openinference-instrumentation-openai-agents`, **plus** the SDK's own
OpenAI client instrumented by `openinference-instrumentation-openai` — two
instrumentors in one process, both left on.

**What it does.** A planning agent runs a 25-turn loop: each turn it calls
one of two tools (`check_inventory(item)` or `place_order(item, qty)`), and
the framework resends the full conversation history to the model on every
turn, as agent frameworks do. The stub model's reply at turn *t* depends
only on *t*, so the loop is deterministic and always 25 turns.

**Scenario, fixed.** Alternate `check_inventory` and `place_order`; the last
turn is a final answer with no tool call.

**Why this shape.** History echo at scale (turn *t* carries *t−1* prior tool
results), and two instrumentors claiming the same underlying call.

---

## Z4 — `streaming-concierge`: streamed completions and tool-call deltas under OpenTelemetry GenAI

**Framework and instrumentation.** No agent framework — a bare `openai`
client, instrumented by the OpenTelemetry GenAI instrumentation for OpenAI
(`opentelemetry-instrumentation-openai-v2`), with the GenAI semantic
conventions' **content capture turned on** via the environment variable the
instrumentation documents. Hand-written agent loop using only the SDK's
tracer for one manual span around the whole conversation (allowed by the
contract: a single manual span, nothing inside it).

**What it does.** A hotel concierge handles a three-message conversation
with `stream=True` on every completion; the second completion streams a
tool call (`book_table(time, party)`) as deltas; the agent executes it and
streams the final answer.

**Scenario, fixed.** Three user messages; one tool call; the stub streams
each reply as at least eight chunks.

**Why this shape.** Streaming spans whose end time is the last chunk, tool
calls assembled from deltas, and the GenAI conventions rather than
OpenInference — the second dialect, carrying content.

---

## Z5 — `flaky-fetcher`: tool errors, retries and an unfinished root under OpenInference / LangGraph

**Framework and instrumentation.** LangGraph (a small state graph with a
retry edge), instrumented by `openinference-instrumentation-langchain`.

**What it does.** A fetch-and-summarize agent calls `http_get(url)`, which
**raises** on the first two calls (a scripted `ConnectionError`) and succeeds
on the third; the graph's retry edge re-enters the tool node each time; then
one LLM summary. After the final answer the process **exits via
`os._exit(0)` without calling `shutdown()`** — the one place the contract's
flush rule is deliberately broken, on the brief's instruction — so the last
batch may never leave the process and the root span may never be exported.

**Scenario, fixed.** One URL; two failures then success; the same summary.

**Why this shape.** Error status on spans, exceptions recorded as span
events, retries as repeated siblings, and a trace whose root is missing or
arrives last — the receiver's completion policies have never met this.

---

## Z6 — `crew-of-three`: multi-agent delegation under OpenInference / CrewAI

**Framework and instrumentation.** CrewAI with three agents and a sequential
process, instrumented by `openinference-instrumentation-crewai`, **and**
`openinference-instrumentation-openai` for the underlying client (two
instrumentors, as in Z3, but across a multi-agent framework).

**What it does.** A "release notes" crew: a *collector* agent calls
`list_commits()` (tool), a *writer* agent drafts notes, a *reviewer* agent
calls `lint_markdown(text)` (tool) and either approves or sends it back
once. Each agent is its own LLM persona; delegation between agents goes
through the framework.

**Scenario, fixed.** Eight canned commits; the reviewer sends the draft back
exactly once, then approves.

**Why this shape.** Agent-to-agent delegation as spans, tasks nested under
agents nested under a crew, and the same model client seen through two
instrumentors across process-internal handoffs.

---

## What every brief has in common

- `make run-recorded` is deterministic; `make run-real` is run once against
  a real model with the endpoint we give.
- The implementer does not know what consumes the traces and does not look.
- Where a brief asks for something the contract forbids (Z4's one manual
  span, Z5's missing shutdown), the brief wins, exactly as far as it says.
