#!/usr/bin/env python3
"""Rewrite asset references in an artifact's files after the assets were re-uploaded.

    python3 rewrite_assets.py <artifact folder> <map.json>

map.json: {"<old asset url or id>": "<new url>", ...}
For a Claude Doc the keys are old blob ids and the values new ones: {"blob/47c1...": "blob/9ab2..."}.
Every file the manifest lists for the artifact (and, for typed artifacts, every file
under project/) is scanned; each old url is replaced with the new one. A bare 32-hex
id on either side is expanded to /_blob/<id>. Prints what changed and any old
reference that is still present afterwards, which means a mapping is missing.
"""
import json, pathlib, re, sys

HEX = re.compile(r"^[0-9a-f]{32}$")


def norm(u):
    return f"/_blob/{u}" if HEX.match(u) else u


def main(folder, map_path):
    folder = pathlib.Path(folder)
    amap = {norm(k): norm(v) for k, v in json.loads(pathlib.Path(map_path).read_text()).items()}
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix in (".html", ".json", ".css", ".js", ".md", ".svg", ".txt")]
    changed = 0
    for p in files:
        s = p.read_text(errors="ignore"); o = s
        for old, new in amap.items():
            s = s.replace(old, new)
        if s != o:
            p.write_text(s); changed += 1
            print(f"rewrote {p.relative_to(folder)}")
    leftover = set()
    for p in files:
        for m in re.findall(r"/_blob/[0-9a-f]{32}|(?<![_/])blob/[0-9a-f]{8}-[0-9a-f]{4}", p.read_text(errors="ignore")):
            if m not in amap.values():
                leftover.add(m)
    print(f"rewrite_assets: {changed} file(s) changed")
    if leftover:
        print("rewrite_assets: references with no mapping (upload these and add them to the map):")
        for u in sorted(leftover):
            print("  " + u)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
