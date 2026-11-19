---
name: autoformalize-business-rules
description: Turn business rules from any source (web pages, PDFs, contracts, code, spreadsheets, SME notes) into cited Lean rules with proofs, open questions and an SME report.
---

# Autoformalize business rules

Use this skill to start or extend a project that writes an organization's
business rules as Lean 4 definitions, proves what they guarantee, and reports
where the sources disagree or are silent. It generalizes two working projects:
`verified-air` (IATA ONE Order) and `delta-skymiles-policies` (Delta SkyMiles),
plus the pitfalls an independent review found in the second.

## Project shape

A project has two layers joined by one contract.

1. **Capture** is specific to each kind of source. An adapter acquires the
   source, keeps an immutable snapshot, and splits it into segments with stable
   ids, hashes and locators. This is the only layer that knows what a PDF, a
   spreadsheet or a code base looks like.
2. **Analysis** is the same for every project. It reads only the capture
   bundle: survey, readings, Lean rules, verification and reports. It never
   touches the network or a raw source.

```
source --adapter--> snapshot --process--> segments.yaml --+--> survey
                                                          +--> Lean rules (cite id + hash)
                                                          +--> golden cases
Lean build --> status.json --> status.md, SME report, specs, oracle
SME answers --> new sme segments --> readings removed --> guarantees proven
```

A new kind of source needs a new adapter and nothing else. If the analysis
layer needs to know where a segment came from, the adapter is leaking.

## Non-negotiable rules

1. Every rule cites the segments it was written from, by id and hash.
2. Where sources disagree or are silent, the undecided point is a parameter
   (a reading). Never pick a reading for the business and then prove the
   guarantee.
3. A guarantee is proven only if it holds under every reading.
4. A choice no source makes is a `modeller` source, named on the rule.
5. Every rule has at least one cited example whose expected value is copied
   from a segment, written before the rule.
6. Statuses and example values are computed by the build. Nobody types one.
7. The model is checked against something it did not produce: cited examples
   and a hand-written golden case file.
8. Summaries of source text are in our words. Sources with a no-reproduction
   notice are cited by locator and hash only.
9. Only the fetch step touches the network. Processing is deterministic.
10. "Proven" means Lean checked a proof for every input. Nothing in the build
    searches for counterexamples, so write "an example shows the rule breaking
    it", never "Lean found".

## Repository layout

```
CLAUDE.md                 project rules for agents (template below)
README.md                 design, commands, decisions
sources/
  manifest.yaml           what to capture (include) and what not (exclude), each with a reason
  raw/                    bytes as acquired, plus acquisition metadata
  processed/<doc>/        built from raw/ only: text.md, segments.yaml, links.yaml
  coverage.md             in-scope material not yet classified, dead links, named but missing documents
src/<pkg>/                capture tooling and reports (Python via uv)
  adapters/<kind>.py      one module per source kind
Rules/Core/               Attributes.lean, Sources.lean, shared types (Money, Time, Party)
Rules/<Area>/             rules by business area, one range of rule IDs per area
Status/Main.lean          lake exe status
Oracle/golden.jsonl       hand-written cases, written from segments without reading the Lean
Oracle/cases.jsonl        cases generated from the model, for checking outside tools only
docs/survey.md            candidate rules and their classification
docs/status.md            generated
reports/sme-review/       generated report for subject matter experts
research/answers.yaml     likely answers to open questions, with sources and confidence
.github/workflows/ci.yml  builds proofs, checks citations, regenerates reports
```

## Stage 0. Scope

Settle these before capturing anything, and record them in the README:

- The domain and the business areas, each with an ID prefix (`MQ-`, `ONE-1xx`).
- The sources, their kinds, and who owns them. List every kind you expect.
- Who answers questions (the SME), even if only a role.
- The outcomes wanted: a review document for SMEs, a test oracle for an
  implementation, implementation proofs, or a policy for a support agent.
- Licensing: which sources may be stored and quoted, which only cited.

Then write `CLAUDE.md` from the template at the end and create the layout.
Use Lean 4 without Mathlib unless a proof needs it. Run Python through uv.

## Stage 1. Capture

### The capture contract

Every adapter emits the same three things. The analysis layer depends on
these and nothing else.

**`sources/manifest.yaml`**

```yaml
scope:                       # what counts as in scope for coverage
  - /skymiles/
include:
  - id: program-rules        # document id, stable, used in segment keys
    kind: policy             # source kind, see the table below
    adapter: web             # which adapter acquires it
    locator: https://example.com/program-rules
    reason: The benefit pages defer to it.
    licence: quote           # quote | summarize | cite-only
exclude:
  - locator: https://example.com/old-page
    reason: Retired offer.
    dead_since: 2026-11-18   # only for material that is gone but still referenced
```

**`sources/raw/<doc>/`**: the bytes as acquired and an `acquire.json` with
time, status, content hash, and the version or commit where one exists.
Raw files are never edited.

**`sources/processed/<doc>/segments.yaml`**: one entry per citable unit.

```yaml
- id: terms-conditions/fn-2          # stable, see rules below
  kind: footnote                     # paragraph | list-item | table-row | footnote | clause
                                     # | definition | function | branch | constant | test
                                     # | rule-row | answer | query-result
  section: [Benefits at Each Tier, Terms]
  locator: "p. 4"                    # page, clause number, file:line@sha, sheet!row
  sha256: 3f1c9a0b2d4e5f61           # first 16 hex of sha256 of the normalized text
  text: Complimentary upgrades apply on qualifying flights...
  # optional structured fields by kind:
  columns: ['', SILVER, GOLD]        # table-row
  cells: [...]
  effective: 2026-02-01              # when the source states one
```

Segment id rules:

- Build the id from structure and content: nearest heading plus opening words,
  a clause number, a footnote marker, a table row's key cells, a qualified
  function name. Never from position alone.
- Inserting or reordering material leaves ids unchanged. Editing a segment's
  text changes its hash and keeps its id.
- Resolve collisions with a numeric suffix in document order.
- Normalize before hashing: Unicode NFC, collapsed whitespace, no markup.
- Output depends only on `raw/` and a `PROCESSOR_VERSION` constant. Changing
  the processor changes ids or hashes, so rerun `citations` and update
  `Sources.lean` for any segment that moved.

**`sources/coverage.md`**: in-scope material found (sitemaps, links, cross
references, "subject to the X Terms") that is in neither `include` nor
`exclude`, plus dead references and the documents that point to them.

Standard commands, whatever the adapters:

```
<cli> acquire [DOC...]   # the only networked or side-effecting step
<cli> process            # raw/ -> processed/, deterministic, deletes and rebuilds
<cli> coverage           # writes coverage.md
<cli> find WORDS [--doc ID]  # search segments to cite
<cli> citations          # every cited id exists with the cited hash; lists rules to review
```

Gate: `process` run twice gives byte-identical output, and every item in
`coverage.md` is classified or has a reason to stay.

### Source kinds

Use these kinds in `Sources.lean` and the manifest. The kind tells a reader
how much weight a source carries.

| Kind | Meaning |
|---|---|
| `standard` | A published industry standard |
| `regulation` | A law or regulation |
| `policy` | The organization's own published or internal policy, terms, contract |
| `engine` | A rule set running in production (decision tables, DMN, Drools) |
| `code` | Application source code |
| `test` | An existing test suite |
| `data` | Production data or logs, as a dated query and result |
| `sme` | An answer from a subject matter expert, dated, with a role |
| `modeller` | A choice no source makes |

`code`, `engine`, `test` and `data` say what a system does. `policy`,
`standard` and `regulation` say what should happen. A disagreement between the
two groups is a finding to report.

### Adapters by source

Each adapter section says how to acquire, what one segment is, how to form the
id, and what goes wrong.

**Web pages.** Read `robots.txt` and wait between requests. Detect soft 404s
(status 200 with a "not found" page) and record them as 404. Convert HTML to
Markdown, then segment by paragraph, list item, table row and footnote.
Paragraphs that continue a footnote nest under it. Id: heading slug plus
opening words, or `fn-N`, or `row-<first cell>`. Record outgoing links for
coverage. Keep `sitemap.xml` for discovery. Raw HTML carries per-request
tokens, so keep a new raw file only when processed text changed.

**PDFs.** Extract with layout (`pdftotext -layout`, or `pdfplumber` for tables).
Rebuild headings from numbering or font size, join hyphenated lines, drop
running headers and footers. Locator is the page. Scanned pages need OCR; mark
those segments `ocr: true` with a confidence and check every number cited from
them by hand.

**Contracts, terms and regulations.** The clause number is the id
(`s4.2(b)`). Definitions are `kind: definition` and every rule using a defined
term cites its definition. Record cross references ("subject to clause 14") as
links so coverage can follow them. Amendments and effective dates become
`effective` fields or separate dated documents; never overwrite an old
version.

**Spreadsheets and rate tables.** One row is one segment. Id is
`<sheet>/<key columns>`. Record the header row as `columns`. Capture a formula
as text and its computed value. Expand merged cells. Record units and
currency. Large tables become generated Lean (see Stage 4), each row citing
its segment.

**Code.** Pin a commit. A segment is a function, a branch of a conditional, or
a named constant. Id is the qualified name, plus a branch label
(`pricing.fare_for#basic`). Locator is `file:line@sha`. Capture conditions and
literals in `text`. Kind is `code`: it shows what the system does, and the
model compares it with policy. Tree-sitter or the language's own AST is better
than regex.

**Rules engines.** A rule row or a decision-table row is a segment. Id is
`<table>/<rule id>`. Capture hit policy and priority, since they decide which
row wins.

**Test suites.** A test case is a segment with its inputs and expected output.
These are ready-made golden cases after an SME confirms them.

**Data and logs.** Never store raw records. A segment is a named query, its
result and the date. Use data to show what happens in practice and to confirm
or refute a reading.

**SME answers, interviews and email.** One answer is one segment, with date,
role and the question it answers. Store the question id so the report can
close it.

**Sources with a no-reproduction notice.** Keep raw and processed text out of
git (local only, ignored). Commit only locator, id and hash. Summaries are in
our words and quote nothing.

**Tickets and wikis.** Pin the page version. A segment is a paragraph or a
comment, id from the heading and opening words.

A new kind of source gets an adapter module and a section in the README that
answers the same four questions.

## Stage 2. Survey

Before writing Lean, list candidate rules in `docs/survey.md`. For each:

- an ID in its area's range, a one-line statement in our words, and the
  segments it rests on;
- **type**: `decision` (the system decides something) or `invariant` (a
  property that holds across objects or over time);
- **clarity**: `clear` (a source states it), `vague` ("may", "should",
  "typically", an undefined term), `silent` (a source names the situation and
  gives no rule) or `conflict` (two segments give different rules);
- for vague, silent and conflict, the open point the business must decide.

Vague, silent and conflicting candidates are the most valuable: writing them
in Lean forces a decision that belongs to the business. If the domain has a
capability list (IATA ARMI, a product catalog), keep a coverage map of
capabilities against rules.

## Stage 3. Readings and questions

For every cited segment, quote the full sentence with its conditions and list
its qualifiers ("qualifying", "operated by", "if permitted", "typically",
"up to", "at least", dates). Point each qualifier to a branch, a reading or a
`modeller` source.

- A reading is an inductive type passed as a parameter:
  `inductive Rounding | down | nearest`. Each constructor cites the segment
  that supports it.
- Give each reading a `likely` flag and a one-line reason. A reading few
  readers would take still gets a parameter if the text supports it, but the
  report ranks it low.
- Search sibling rules for the same concept and reuse their reading type.
- Record each question for the business once, with the readings that answer
  it. Two rules answering the same question share it.
- Where an adjustment is stated relative to an old value ("an additional $50"),
  record the old value as a dated or `modeller` source. Never add the
  adjustment to a table that already includes it.

Classify every question as `conflict` (sources disagree) or `unstated`
(sources are silent) for the report.

## Stage 4. Write the rules

### Rule template

```lean
/-- EARS: When <trigger>, the system shall <response>.

Story: As a <role>, I want <goal>, so that <benefit>.

Acceptance criteria:

* MQ-001.1: When a member's balance meets a tier's threshold, the system
  shall give the member that tier or a higher one.
* MQ-001.2: ...
-/
@[ears "MQ-001", source "htq-thresholds htq-threshold-year"]
def tierFor (t : Thresholds) (balance : Nat) : Tier := ...

/-- htq-thresholds: "Gold 10,000". Given 10,000 MQDs, the tier is Gold. -/
@[cited_example "htq-thresholds", checks "MQ-001.1"]
example : tierFor howToQualify 10000 = .gold := by decide

@[checks "MQ-001.1"]
theorem tierFor_monotone (t : Thresholds) (a b : Nat) (h : a ≤ b) :
    tierFor t a ≤ tierFor t b := by ...
```

Examples state Given, When and Then in the docstring and return records whose
fields label each part.

### Attributes

| Attribute | On | Meaning |
|---|---|---|
| `@[ears "ID"]` | rule | Stable requirement ID. Never renumber. |
| `@[source "k1 k2"]` | rule, reading | Keys in `Rules/Core/Sources.lean`. An unknown key is an error. |
| `@[checks "ID.n"]` | theorem, example | Proves that criterion for every input. |
| `@[cited_example "key"]` | example | Expected value copied from that segment, quote in the docstring. |
| `@[case]` | def | A computed scenario, used to witness a disagreement. |
| `@[question "text"]` | theorem | A proven disagreement between readings, and the question for the business. |
| `@[transcription]` | theorem | Checks that two hand-typed copies match. Counted apart from guarantees. |
| `@[trivial_ok "reason"]` | theorem | Allows a `rfl` or bare `decide` proof under `@[checks]`. |
| `@[confirmed method "date" "who" "what" "fingerprint"]` | rule | An SME, production data or a second independent source confirmed it. Only for a confirmation that happened. |

### Theorem kinds

- **Guarantee.** Holds under every reading, for every input. Tag `@[checks]`.
- **Disagreement.** The readings give different answers:
  `theorem catalogs_disagree : ∃ c d t o, offered c t o ≠ offered d t o := ⟨…, by decide⟩`,
  tagged `@[question "..."]`. This replaces a false theorem closed with
  `sorry`. The build then has no `sorry`.
- **Guarantee for one reading.** Named `<guarantee>_of_<reading>`, no
  criterion tag, docstring names the reading. The report shows it under "if
  the business decides this".
- **Properties that relate inputs.** Monotonicity, invariance under
  permutation where the text treats inputs as a set, totals equal to the sum
  of their parts, limits under every reading. A wrong rule can fail these.

Existing projects that still mark open questions as `@[open_question]` with
`sorry` and an `@[case]` should move to disagreement theorems as their own
change, because the status and report counts change.

### Lean hygiene

- State theorems over `Nat` and `Int`, not type aliases: `omega` does not see
  through aliases.
- One function per business question. If two must exist, prove they agree
  under matching readings.
- A total calls the functions for its parts. No free `Nat` argument stands in
  for a value the model already computes.
- An unknown is `Option` or a reading. No literal stands for "not modeled" or
  "typically".
- `head?`, `find?` and `getD` on policy data choose silently. Return the list
  or take a reading.
- Generate large tables from segments (a `gen-*` command writing a Lean file
  that cites each row). Never edit generated files; change the generator.
  CI regenerates them and fails on a diff.
- Cross-page agreement checks mean something only when both sides are
  generated from the snapshot. Otherwise tag them `@[transcription]`.

## Stage 5. Verify

### The status tool (`lake exe status`)

It reads attributes and the axioms each declaration uses, writes
`build/status.json` and `docs/status.md`, and fails on:

- any `sorry`;
- a rule with no `@[source]` or no `@[cited_example]` from one of its sources;
- `@[checks]` naming an unknown criterion, or a criterion with nothing checking it;
- a `@[checks]` theorem whose proof term after its binders is `Eq.refl` or
  `of_decide_eq_true` with no hypotheses, unless it has `@[trivial_ok]`;
- a `@[question]` theorem that is not an existence statement over readings.

Status per criterion: `proven` (a guarantee), `question` (a proven
disagreement), `transcription`, `unchecked`.

### Citations

`citations` fails when a cited segment is gone or its hash changed, and lists
the rules to review. It also reports numeric literals in a rule that appear in
none of its cited segments.

### Golden cases

`Oracle/golden.jsonl` is written from segments by someone who has not read the
Lean. In an agent session, give that job to a subagent with access to
`sources/processed/` and no access to `Rules/`. Each case:

```json
{"id": "g-cb-012", "segment": "choice-benefits/cb26-gift-terms", "sha256": "…",
 "quote_or_summary": "up to four recipients", "input": {...}, "expected": {...}}
```

The build fails when the model disagrees with a settled golden case. A case
that lands on an open question records the readings instead.

The generated oracle (`Oracle/cases.jsonl`, from `lake exe oracle`) checks
outside tools against the model. It cannot find a mistake in the model,
because every case inherits it.

### Independent critique

After each area, run a fresh-context review that compares every rule with the
full text of the segments it cites, ranks findings by how much they change
what the model tells a reader, and writes them to `reviews/`. Each new kind of
mistake becomes a pitfall in the checklist below and, where possible, a check
in the status tool.

### Implementation checks (optional)

To check a service against the model, from quick to complete: fixed request
vectors with the model's answers; property tests that compare the service with
the running oracle and restate each theorem as a property; translating the
code into Lean (Aeneas for Rust) and proving it equal to the model.

## Stage 6. Report

All reports are generated from `build/status.json` and the snapshot, and
committed with the rules they describe.

- `docs/status.md`: every rule, criterion and status, with sources.
- The SME report: discrepancies between cited segments, side by side; the
  questions ranked by `likely` flag and by how many criteria depend on them;
  each question's readings and what each reading gives; dead references; the
  sources the analysis rests on, with capture dates. Show dates in the SME's
  time zone and label it.
- Optional: EARS requirement specs (one folder per module, Kiro layout), CSV
  exports with fixed URLs, a dependency graph.

Wording in reports: proven means checked for every input; an open point is a
question for the business; nothing is confirmed until an `@[confirmed]` tag
says so.

## Stage 7. Close the loop

- An SME answer becomes an `sme` segment. The reading it settles is removed or
  fixed, the `_of_<reading>` theorem becomes the guarantee, and the question
  closes in the report.
- A confirmation becomes `@[confirmed ...]` with the rule's fingerprint from
  `status.json`. A rule edited afterwards shows as confirmed but out of date.
- To refresh sources: `acquire`, `process`, regenerate tables, `coverage`,
  `citations`. Keep new raw files only when processed text changed. Review the
  rules `citations` lists.

## CI

One workflow, on push and pull request:

1. Capture job: `citations`, regenerate generated Lean and fail on a diff.
2. Lean job: `lake build`, `lake exe status`, fail if `docs/status.md`
   differs from the committed copy, check golden cases.
3. Report job: regenerate the oracle and SME report. On a same-repository
   pull request branch it may push a "Regenerate reports" commit.

Cloud agent sessions often cannot download the Lean toolchain. Let CI build
Lean and regenerate reports, and push a branch to see results.

## Pitfalls checklist

Copy into each pull request that adds or changes a rule.

- [ ] P1. Every `@[checks]` theorem could fail for some wrong version of the
      rule. A theorem that cannot is `@[transcription]`.
- [ ] P2. Disagreements are proven existence statements with `@[question]`.
      No false theorem is closed with `sorry`.
- [ ] P3. Every qualifier in the cited segments maps to a branch, a reading or
      a `modeller` source. Sibling rules reuse the same reading type.
- [ ] P4. Where the text treats inputs as a set or as rising, a permutation or
      monotonicity theorem exists. Theorems vary the inputs the bug would
      depend on.
- [ ] P5. The rule has a cited example with the value copied from a segment.
      Adjustments described relative to an old value use a recorded old value.
- [ ] P6. Each reading quotes its full sentence and carries a `likely` flag.
- [ ] P7. No `head?`, `find?` or `getD` chooses among policy entries without a
      reading.
- [ ] P8. One function per business question, or a theorem that two agree.
- [ ] P9. Totals call the functions for their parts.
- [ ] P10. Unknowns are `Option` or readings, never a literal.
- [ ] P11. New behaviour has a golden case written without reading the Lean.
      The generated oracle is never used to check the model.
- [ ] P12. Every row and value the rule reads is cited.

## Templates

### Sources.lean entry

```lean
{ key := "htq-thresholds", kind := .policy,
  doc := "how-to-qualify",
  segment := "mqd-thresholds-for-status/row-5-000-mqds", sha256 := "a928f714b9cf815f",
  summary := "MQD thresholds: Silver 5,000, Gold 10,000, Platinum 15,000, Diamond 28,000." },
{ key := "modeller-cabin-order", kind := .modeller,
  summary := "Comfort Basic ranks above Main Classic. No source states an order." },
```

### CLAUDE.md for a new project

```markdown
# CLAUDE.md

<Domain> rules as Lean, citing a versioned snapshot of <sources>. The README
explains the design; read it before changing structure.

## Capture
- Python runs through uv only.
- `acquire` is the only step that touches the network. Everything else reads the snapshot.
- Add or drop sources in `sources/manifest.yaml`, each with a reason and kind.
- Changing a processor changes ids or hashes: rerun `process`, then `citations`,
  and update `Rules/Core/Sources.lean`.
- Never edit generated Lean; change the generator and regenerate.

## Rules
- Every rule cites its segments and has a cited example written first.
- Where sources disagree or are silent, take the point as a reading. Never pick
  one for the business. Disagreements are proven with `@[question]`; no `sorry`.
- A choice no source makes is a `modeller` source, named on the rule.
- Tag `@[checks]` only for a proof over every input that a wrong rule could fail.
- State theorems over `Nat` and `Int`, not aliases.
- After changing Lean: `lake build`, `lake exe status`, commit `docs/status.md`.
  If questions changed, regenerate the oracle and SME report and classify new
  questions as conflict or unstated.
- Run the pitfalls checklist on every pull request.

## Writing
Summaries of source text are in our words. Statuses are computed, never typed.
```

## Order of work for a new project

1. Stage 0, then one adapter and one document end to end: capture, survey three
   candidates, write one rule with a cited example, status tool, CI.
2. Add sources and adapters until coverage is clean for the first area.
3. Write the area's rules, readings and golden cases. Run an independent
   critique and fix what it finds.
4. Generate the SME report and send the questions.
5. Repeat per area. Fold each new kind of mistake back into this checklist.
