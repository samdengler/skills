#!/usr/bin/env python3
"""Turn one Claude Docs tab's markdown export into importable markdown.

    python3 doc_prep_tab.py <raw.md> <sidecar.json> <out.md>

The Docs markdown export loses three things the import has to restore:
  - the byline chips ("Oct 9, 2026 · @Name" on line 3) -> <?claude block asof?> · <?claude block me?>
  - each diagram or chart ("&#91;embedded content: <caption>\\]") -> <?claude block wN?>, in order
  - each image ("&#91;image: <alt>\\]") -> ![<alt>](blob/<old blob id>), rewritten on import
and it writes in-page links as (#<block id>), which mean nothing in another doc. Those become
GitHub-style heading slugs (#references), which the Docs connector resolves on import.

sidecar.json, written by hand from the tab's outline read:
  {"anchors":  {"<block id>": "<heading text, or its first words>"},
   "embeds":   [{"node": "<widget node id>", "caption": "<caption>"}, ...]   in document order,
   "pictures": [{"blob": "<blob id>", "alt": "<alt text>"}, ...]            in document order}

Prints a JSON report and exits 1 when an anchor, embed or picture could not be matched.
"""
import json, re, sys

BYLINE = re.compile(r"^[A-Z][a-z]{2} \d{1,2}, \d{4} · @.+$")
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def slug(t):
    t = t.strip().lower()
    t = re.sub(r"[^\w\- ]", "", t)
    return t.replace(" ", "-")


def main(src, side, dst):
    md = open(src, encoding="utf-8").read()
    sc = json.load(open(side, encoding="utf-8"))
    problems, asof = [], None
    lines = md.split("\n")
    if len(lines) > 2 and BYLINE.match(lines[2]):
        mon, day, year = re.match(r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", lines[2]).groups()
        asof = f"{year}-{MONTHS[mon]:02d}-{int(day):02d}"
        lines[2] = "<?claude block asof?> · <?claude block me?>"
    md = "\n".join(lines)

    caps = []
    def emb(m):
        caps.append(m.group(1))
        return f"<?claude block w{len(caps)}?>"
    md = re.sub(r"&#91;embedded content: (.*?)\\\]", emb, md)
    want = [e["caption"] for e in sc.get("embeds", [])]
    if caps != want:
        problems.append({"embeds": {"in_export": caps, "in_sidecar": want}})

    pics = sc.get("pictures", [])
    seen = []
    def pic(m):
        i = len(seen); seen.append(m.group(1))
        if i >= len(pics):
            return m.group(0)
        return f"![{pics[i]['alt']}](blob/{pics[i]['blob']})"
    md = re.sub(r"&#91;image: (.*?)\\\]", pic, md)
    if len(seen) != len(pics):
        problems.append({"pictures": {"in_export": seen, "in_sidecar": [p["alt"] for p in pics]}})

    heads = re.findall(r"^#{1,6} (.+)$", md, re.M)
    anchors, unmapped = sc.get("anchors", {}), set()
    def fix(m):
        h = anchors.get(m.group(1))
        full = [x for x in heads if h and x.startswith(h)]
        if len(full) != 1:
            unmapped.add(m.group(1)); return m.group(0)
        return f"(#{slug(full[0])})"
    md = re.sub(r"\(#([a-z0-9]+\.[0-9]+)\)", fix, md)
    if unmapped:
        problems.append({"unmapped_anchors": sorted(unmapped)})

    open(dst, "w", encoding="utf-8").write(md)
    print(json.dumps({"asof": asof, "widgets": len(caps), "pictures": len(seen),
                      "bytes": len(md.encode()), "problems": problems}, indent=1))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
