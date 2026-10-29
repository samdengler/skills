---
name: "artifact-exchange"
description: Export Claude artifacts (published pages, Claude Docs with their tabs and diagrams, Slides decks, other typed artifacts, and the skills they depend on) into one portable zip bundle, and import such a bundle into another Claude account as new or updated artifacts, with Docs coming back as real Docs. Use this whenever the user wants to move, copy, share, back up, hand off, or sync artifacts between accounts, workspaces, or computers (personal to work, one org to another), asks how to "export" or "import" an artifact, attaches a file named *-bundle.zip or a folder with manifest.json, or wants the same artifact editable in two places. Also use it when a user asks to package an artifact for someone who cannot open the share link.
---

# Artifact exchange

Artifacts belong to the account that published them, and no share link makes one editable in another account. This skill moves them as files: an **export** writes every artifact into a bundle with a manifest, and an **import** reads the bundle and publishes each artifact into the current account. The manifest records where each artifact came from and where it landed, so the same bundle can travel back and update the originals.

## Order of work

1. Decide the direction: export (artifacts in this account go out) or import (a bundle came in). A bundle that has already been imported here and edited since is an export again.
2. Export: read every artifact in full, write the bundle folder, record each artifact with `add_artifact.py`, pack with `bundle.py pack`, send the zip with SendUserFile, and give the user the import prompt from the README.
3. Import: unpack with `bundle.py unpack`, read the manifest, publish each artifact the way its kind requires, record the new url with `record_import.py`, repack, and send the updated bundle back so the round trip is possible.
4. Report a table: artifact, source url, new url, what could not be carried over.

Never rebuild an artifact from memory or from a summary. Every file goes into the bundle exactly as the artifact serves it, and comes out the same way.

## The bundle

A zip named `<name>-bundle.zip` holding:

```
manifest.json            what is inside, where it came from, where it went
README.md                for a person: contents, and the prompt to paste on import
artifacts/<slug>/        one folder per artifact
  index.html             page artifacts: the page itself
  <published files>      page artifacts: any supporting files, at their published paths
  project/...            typed artifacts: the artifact's own files (deck.json, slides/*.html, ...)
  doc.json               Claude Docs: the tabs, in order, and what each one holds
  tabs/NN-<tab>.md       Claude Docs: each tab's markdown, ready to import (chips and diagrams as tokens)
  tabs/raw/NN-<tab>.md   Claude Docs: each tab's markdown export as the connector gave it, for checking
  widgets/<node>.tsx     Claude Docs: each diagram or chart's code
  assets/<id>.<ext>      uploaded assets, named by their asset id
  sources/...            optional: build sources (body.html, .mmd, scripts) when the page was generated
skills/<name>.zip        optional: skills the artifacts depend on
```

`manifest.json`:

```json
{
  "bundle_version": 1,
  "name": "launch-review",
  "exported_at": "2026-09-23T15:00:00Z",
  "origin": {"label": "personal claude.ai"},
  "artifacts": [
    {
      "slug": "launch-plan",
      "title": "Launch plan for the billing service",
      "kind": "page",
      "files": ["index.html"],
      "assets": [],
      "note": "built with the technical-design-doc skill from sources/body.html",
      "history": [
        {"action": "exported", "url": "https://claude.ai/artifact/...", "label": "personal claude.ai", "when": "..."},
        {"action": "imported", "url": "https://claude.ai/artifact/...", "label": "work claude.ai", "when": "..."}
      ]
    },
    {
      "slug": "review-deck",
      "title": "Launch review deck",
      "kind": "typed",
      "type": "Slides",
      "files": ["project/deck.json", "project/slides/cover.html"],
      "assets": [{"file": "assets/7b67...71.png", "id": "7b67...71", "url": "/_blob/7b67...71"}],
      "history": []
    }
  ],
  "skills": ["technical-design-doc.zip"]
}
```

`kind` is `page` for a hand-built HTML artifact, `typed` for one made from an Artifact type (Slides, Sheets, Design, and so on), and `doc` for a Claude Doc; `type` names the type (`Docs` for a doc). A Claude Doc is never `typed`: its content lives in the Claude Docs service, not in the artifact's files, so a typed export of it carries nothing and its import comes back as a page. An artifact is a Doc when `mcp__Claude_Docs__read` on its link returns `files` (its tabs). `aliases` lists the artifact's other url forms (the short `claude.ai/artifact/<id>` link and the `claude.ai/code/artifact/<uuid>` link), so links to it can be found in other artifacts. `history` is the round-trip record: the newest `imported` entry whose `label` matches the current account is the artifact to update on a later import.

## Exporting

1. Ask which artifacts, if the user did not say. `Artifact list` shows them; the user may also give urls.
2. Create the bundle folder in the scratchpad: `python3 scripts/bundle.py init <folder> "<name>"`. Set `origin.label` in `manifest.json` to a short name for this account ("personal claude.ai", "work Cowork"); the user supplies it if unclear.
3. For each artifact, read it in full with the Artifact tool and save the files under `artifacts/<slug>/`. First find out whether it is a Claude Doc: `mcp__Claude_Docs__read(ref={"object":"project","id":"<link>"})` returns `files` for a Doc and refuses anything else.
   - **Claude Doc.** Follow `references/export-doc.md`: per tab, the connector's markdown export, the outline, `doc_prep_tab.py`, every widget's code, and every image. Several docs can be exported in parallel, one sub-agent per doc; run `add_artifact.py` yourself afterwards, one at a time, because the agents would race on `manifest.json`. Never export a Doc through the Artifact tool's files or as a page.
   - **Page artifact.** `read` with the url returns the page; the result names a saved copy of the full HTML. Copy that file to `index.html`. Then `list` with `scope: "files"` and `read` each published file with `path`, saving each at its published path. The saved copy from `read` has a small wrapper `<head>` above the page's own `<!DOCTYPE html>`; strip everything before the page's own doctype so `index.html` is the page as authored.
   - **Typed artifact.** `list` with `scope: "files"`; read every file under `project/` with `paths` (several per call) and save each at its path. Never copy `index.html`, `SKILL.md`, or anything under `artifact-type/`; those belong to the type and the importing account has its own. Record the type's name from the read result.
   - **Assets, both kinds.** `list` with `scope: "assets"`; `read` each asset by its id with `path`, and save the file as `assets/<id>.<ext>`, extension from the reported media type. Page artifacts reference assets as `/_blob/<id>` in their HTML; typed ones in their project files.
   - **Sources, optional.** When the page was generated (a design doc built from `body.html` and `.mmd` files, a deck rendered from a script), copy the sources under `sources/` so the other side can keep editing from source, and add a `note` saying which skill builds it.
4. Record each artifact: `python3 scripts/add_artifact.py <folder> <slug> --title "..." --kind page|typed|doc [--type Slides] --url <artifact url> [--alias <other url form>] --label "<origin label>" [--note "..."]`. The script lists the files and assets it finds and appends the `exported` history entry.
5. Skills: if a bundled artifact depends on a skill the user installed (the `note` names it), and the skill's zip is available, copy it to `skills/` and list it in the manifest's `skills`. A skill the account provides by default is not bundled. When the bundle holds a Doc, also bundle this skill itself (`skills/artifact-exchange.zip`), since an older copy on the other side cannot import Docs.
6. Write `README.md` from the template in `assets/README-template.md`: one line per artifact, then the import prompt with the bundle name filled in.
7. `python3 scripts/bundle.py pack <folder> <name>-bundle.zip`. The pack step validates the manifest and refuses a bundle with a missing file. Send the zip with SendUserFile and give the user the import prompt in the reply as well, since they will paste it in the other app.

Comments on an artifact do not travel; say so if the artifact has threads the user cares about.

## Importing

1. Save the attached zip to the scratchpad and run `python3 scripts/bundle.py unpack <zip> <folder>`. It prints each artifact, its kind, and its history. Read `manifest.json` and `README.md`.
2. Ask for this account's label if the manifest's `origin.label` does not obviously differ from it ("work claude.ai"). Then decide per artifact:
   - A `history` entry with `action: imported` and this account's label exists: this is an update. Read that url with the Artifact tool first (a publish to an unread artifact is refused), then publish to it.
   - Otherwise: create a new artifact.
3. Publish each artifact:
   - **Claude Doc.** Follow `references/import-doc.md`: create every doc empty first with all its tabs, record each new url, run `rewrite_links.py` so links between bundled artifacts point at the new copies, then add images, widgets and text through the Docs connector, and check every tab with `doc_compare.py`. Never publish a Doc's markdown or HTML with the Artifact tool, and never upload markdown as an asset: the first makes a page, and each upload asks the person for approval. For an update, read the existing doc, `replace` each tab's top-level blocks (ids from an outline read, `ifRev` from that read) with one placeholder paragraph, then continue at the doc's step 3; tabs the bundle no longer has are left for the person to remove.
   - **Page artifact.** Upload each file under `assets/` first (`publish` with `asset: true` and the file path, or `file_paths` for several); the result gives each new url. Write `map.json` with `{"<old id>": "<new url>"}` and run `python3 scripts/rewrite_assets.py artifacts/<slug> map.json`; it rewrites every `/_blob/<old>` and lists any reference it could not map. Then publish `index.html` (with `url` for an update, without it for a new artifact), passing the other published files through `files`. Keep the page's own `<title>` and pass `icon` on a first publish.
   - **Typed artifact.** Call `Artifact(action="list", scope="types")` to find the type in this account, create the artifact from the type's `type_url` with the manifest's `title` (new) or read the existing url (update). Upload the assets to that artifact, run `rewrite_assets.py` on `artifacts/<slug>` with the map, then publish `project/deck.json` (or the type's index file) as `file_path` with every other `project/` file in `files`, `root` set to the artifact folder. Follow the type's own instructions from the create result for anything the type requires beyond the files; a Slides deck, for example, keeps `createdOnFiles` as the manifest's index carries it. If the type is not offered in this account, say so and deliver the files instead.
   - **Sources and skills.** If `skills/` holds a zip the user has not installed, tell them the artifact was built with it and where the zip is; do not install it silently. Keep `sources/` in the folder and mention it when the user later asks to edit the artifact from source.
4. After each publish (for a Doc, right after its empty birth), `python3 scripts/record_import.py <folder> <slug> --url <new url> --label "<this account label>"`. Run `python3 scripts/rewrite_links.py <folder> "<this account label>"` once every artifact has its new url and before any content is written, so links between bundled artifacts point at the new copies.
5. Repack: `python3 scripts/bundle.py pack <folder> <name>-bundle.zip` and send it back with SendUserFile. The returned bundle is what makes the next trip an update instead of a copy.
6. Report the mapping table and anything not carried over: comment threads, sharing settings, a type missing here, a file the tool refused.

## Round trips

Edits on either side are exported the same way; the manifest's history tells the importing side which artifact to update. When both sides edited the same artifact since the last exchange, there is no merge: say so, show the two versions' dates from the history, and ask which wins before publishing.

## What does not travel

Sharing settings, comment threads, version history, and the artifact's id. Pinned status is not carried. In a Claude Doc, mentions of people other than the author come back as plain "@Name" text, and links to artifacts outside the bundle still point at the origin account. A Doc needs the Claude Docs connector on the importing side; without it, say so and hand over the tab markdown as files.

## Scripts

- `scripts/bundle.py init|pack|unpack`: manifest scaffold, validation and zipping, unzipping with a summary.
- `scripts/add_artifact.py`: record an artifact's files, assets, and export history from its folder.
- `scripts/rewrite_assets.py`: replace old `/_blob/<id>` references with the new urls after re-upload; fails when a reference has no mapping.
- `scripts/record_import.py`: append the new url to an artifact's history after publishing.
- `scripts/rewrite_links.py`: point links between bundled artifacts at their new urls in this account.
- `scripts/doc_prep_tab.py`: turn a Doc tab's markdown export into importable markdown (byline chips, diagram and image tokens, in-page links).
- `scripts/doc_chunk.py`: split a Doc tab into pieces small enough for one Docs write each.
- `scripts/doc_compare.py`: compare an imported Doc tab's export with the original export.
- `references/export-doc.md` and `references/import-doc.md`: the Doc steps in full.
