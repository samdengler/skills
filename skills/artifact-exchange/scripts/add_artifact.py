#!/usr/bin/env python3
"""Record an artifact in a bundle manifest from the files already saved in its folder.

    python3 add_artifact.py <bundle folder> <slug> --title "..." --kind page|typed|doc [--type Slides] \
        --url <source artifact url> [--alias <other url form> ...] --label "<account label>" [--note "..."]

Scans artifacts/<slug>/ and lists every file (excluding assets/) under "files" and every
file under assets/ under "assets" (id taken from the file stem when it is a 32-hex id).
For a Claude Doc (--kind doc) the folder holds doc.json, tabs/, widgets/ and assets/ (see SKILL.md).
Appends a history entry {"action": "exported", ...}. Re-running updates the entry in place.
"""
import argparse, datetime, json, pathlib, re

HEX = re.compile(r"^[0-9a-f]{32}$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle"); ap.add_argument("slug")
    ap.add_argument("--title", required=True); ap.add_argument("--kind", required=True, choices=["page", "typed", "doc"])
    ap.add_argument("--type"); ap.add_argument("--url", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--alias", action="append", default=[], help="another url for the same artifact (short and uuid forms)")
    a = ap.parse_args()
    bundle = pathlib.Path(a.bundle); base = bundle / "artifacts" / a.slug
    if not base.is_dir():
        raise SystemExit(f"add_artifact: no folder {base}")
    files, assets = [], []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()
        if rel.startswith("assets/"):
            stem = p.stem
            assets.append({"file": rel, "id": stem if HEX.match(stem) else None, "url": f"/_blob/{stem}" if HEX.match(stem) else None})
        else:
            files.append(rel)
    mp = bundle / "manifest.json"; m = json.loads(mp.read_text())
    entry = next((e for e in m["artifacts"] if e["slug"] == a.slug), None)
    if entry is None:
        entry = {"slug": a.slug}; m["artifacts"].append(entry)
    entry.update({"title": a.title, "kind": a.kind, "files": files, "assets": assets, "note": a.note})
    if a.kind == "doc": entry["type"] = "Docs"
    if a.type: entry["type"] = a.type
    if a.alias: entry["aliases"] = sorted(set(entry.get("aliases", []) + a.alias))
    entry.setdefault("history", []).append({
        "action": "exported", "url": a.url, "label": a.label,
        "when": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    mp.write_text(json.dumps(m, indent=1))
    print(f"add_artifact: {a.slug}: {len(files)} file(s), {len(assets)} asset(s) recorded")


if __name__ == "__main__":
    main()
