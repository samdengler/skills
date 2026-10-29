# Exporting one Claude Doc

A Claude Doc's content lives in the Claude Docs service, not in the artifact's files, so the Artifact tool's
file listing shows only the Docs type's own files.  Export it through the Docs connector instead.
Tools: mcp__Claude_Docs__read, mcp__Claude_Docs__create (load both with ToolSearch "select:..."), the
Artifact tool (read only), Bash, Write.  Never publish or upload anything during an export.

Folder: `artifacts/<slug>/` with `doc.json`, `tabs/<NN>-<tab-slug>.md`, `tabs/raw/<NN>-<tab-slug>.md`,
`tabs/<NN>-<tab-slug>.side.json`, `widgets/<node id>.tsx`, `assets/<asset id>.<ext>`.
S = the skill's `scripts/` folder.  D = the doc's id (the UUID or the 22-character id from its link).

1. `read(ref={"object":"project","id":D})` → the doc's `name`, its `tabs` map (name, order, subtabOf) and
   `files` (each tab's file id and its prose body id).  C = `{"kind":"project","id":D}`.
2. For each tab, in tab order (NN = 01, 02, ...):
   a. Markdown export: `create(object="blob", engine="blob", container=C,
      payload={"from":{"object":"file","id":<tab file id>},"format":"markdown"})` → `data.asset`.  Then
      `Artifact(action="read", url=<doc link>, path=<asset>)` saves it; copy it to `tabs/raw/NN-<tab-slug>.md`.
      The ack's `notes` count the widgets and images the export replaced with placeholders.
   b. Outline: `read(ref={"object":"node","id":<body id>}, engine="prose", container=C,
      payload={"projection":"outline"})`; follow `next` until `complete`.  Collect, in document order:
      every `<embed>` (its `ref` node id and `caption`), every picture (its blob ref and alt or caption), and
      the text of every heading whose block id appears as `(#<block id>)` in the raw markdown
      (`grep -o '(#[a-z0-9]*\.[0-9]*)' raw.md | sort | uniq -c`).
   c. Write `tabs/NN-<tab-slug>.side.json`: `{"anchors":{"<block id>":"<heading text>"},
      "embeds":[{"node":...,"caption":...}], "pictures":[{"blob":"<blob id>","alt":...}]}`.  Heading text may be
      the first words when the outline truncates it; it must match one heading only.
   d. `python3 -I S/doc_prep_tab.py tabs/raw/NN.md tabs/NN.side.json tabs/NN.md` must print `"problems": []`.
   e. Each embed: `read(ref={"object":"node","id":<node>}, engine="widget", container=C)` → `value.code`.
      Write it to `widgets/<node>.tsx` with the Write tool, byte for byte (no reformatting, no trailing
      newline added).  Note any `blob/<id>` the code cites.
   f. Each picture: `read(ref={"object":"blob","id":<blob id>}, container=C)` gives its asset id; save the
      asset with `Artifact(action="read", url=<doc link>, path=<asset id>)` and copy it to
      `assets/<asset id>.<ext>`.  Do the same for any blob a widget cites.
3. Write `doc.json`:
   ```json
   {"name": "<doc name>", "source_id": "<D as a UUID>",
    "tabs": [{"name": "Deep Dive", "order": "a0", "file": "tabs/01-deep-dive.md",
              "raw": "tabs/raw/01-deep-dive.md", "asof": "2026-10-09",
              "widgets": [{"token": "w1", "node": "<old node id>", "caption": "...", "file": "widgets/<node>.tsx", "blobs": []}],
              "pictures": [{"blob": "blob/<old id>", "asset": "<asset id>", "asset_file": "assets/<asset id>.png", "alt": "..."}]}]}
   ```
   `asof` is the date doc_prep_tab.py printed (null when the tab has no byline).  Tokens w1, w2, ... are in
   document order within each tab, as doc_prep_tab.py numbered them.
4. Record it: `python3 S/add_artifact.py <bundle> <slug> --title "<name>" --kind doc --url <uuid link>
   --alias <short link> --label "<origin label>"`.

Comment threads, version history and sharing do not travel.  Mentions of people other than the author
export as plain "@Name" text and come back as text.
