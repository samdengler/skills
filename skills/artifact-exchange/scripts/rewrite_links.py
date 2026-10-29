#!/usr/bin/env python3
"""Point links between bundled artifacts at their copies in this account.

    python3 rewrite_links.py <bundle folder> "<this account label>"

Bundled artifacts often link to each other (a summary to its deep dives). Their files still
hold the origin account's urls. For every artifact in the manifest that already has an
"imported" history entry for this label, each of its origin urls (the "exported" url and any
"aliases") is replaced with the new url, in every .md, .html and .json file under artifacts/ (a Doc's tabs/raw/ exports are left as exported).
Both url forms are matched: claude.ai/artifact/<short id> and claude.ai/code/artifact/<uuid>.

Run it after every artifact has been created here (a Doc's birth gives its url before any
content is written) and before any content is written. Prints what changed, and lists links
to claude.ai artifacts that stay unmapped (artifacts outside the bundle).
"""
import json, pathlib, re, sys

ID = re.compile(r"https://(?:preview\.)?claude\.ai/(?:code/)?artifact/(?:[^/\s)\"']*-)?([A-Za-z0-9]{22}|[0-9a-f-]{36})")


def key(url):
    m = ID.search(url)
    return m.group(1) if m else None


def main(folder, label):
    folder = pathlib.Path(folder)
    m = json.loads((folder / "manifest.json").read_text())
    amap = {}
    for a in m["artifacts"]:
        hist = a.get("history", [])
        new = next((h["url"] for h in reversed(hist) if h["action"] == "imported" and h["label"] == label), None)
        if not new:
            continue
        olds = [h["url"] for h in hist if h["action"] == "exported"] + a.get("aliases", [])
        for o in olds:
            k = key(o)
            if k:
                amap[k] = new
    changed, unmapped = 0, set()
    for p in (folder / "artifacts").rglob("*"):
        if not p.is_file() or p.suffix not in (".md", ".html", ".json") or "raw" in p.parts:
            continue
        s = p.read_text(encoding="utf-8")
        def sub(mt):
            k = mt.group(1)
            if k in amap:
                return amap[k]
            unmapped.add(mt.group(0)); return mt.group(0)
        o = ID.sub(sub, s)
        if o != s:
            p.write_text(o, encoding="utf-8"); changed += 1
            print(f"rewrote {p.relative_to(folder)}")
    print(f"rewrite_links: {changed} file(s) changed, {len(amap)} origin id(s) mapped")
    for u in sorted(unmapped):
        print(f"  unmapped (outside the bundle): {u}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
